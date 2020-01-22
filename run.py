import yaml
import subprocess
import argparse
import os
import shutil
import shlex
import time
import json


def execute(cmd):
    """
    taken from:
    https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
    """

    popen = subprocess.Popen([cmd], stdout=subprocess.PIPE, shell=True, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def create_output_path(output_path: str, overwrite: bool, resume: bool) -> str:
    if overwrite and os.path.exists(output_path):
        print("deleting existing output folder")
        shutil.rmtree(output_path)

    if not overwrite and not resume:
        assert not os.path.exists(output_path), "output folder already exists and won't be overwritten"

    if resume:
        assert os.path.exists(output_path), "there's nothing to resume from"

    if not resume:
        os.mkdir(output_path)

        for p in ["database", "dense", "sparse"]:
            os.mkdir(os.path.join(output_path, p))

        with open(os.path.join(output_path, "log.json"), "w") as log_file:
            json.dump([], log_file)

    return output_path

def amend_args(colmap_command: str, args: dict, image_path: str, output_path: str, database_path: str):
    """
    sometimes we have to add database_path or image_path or workspace_path to the command
    """

    if colmap_command in [
        "feature_extractor",
        "exhaustive_matcher",
        "vocab_tree_matcher",
        "mapper",
        "hierarchical_mapper",
    ]:
        args["database_path"] = database_path

    if colmap_command in [
        "feature_extractor",
        "mapper",
        "hierarchical_mapper",
        "image_undistorter",
    ]:
        args["image_path"] = image_path

    if colmap_command in [
        "stereo_fusion",
        "patch_match_stereo",
    ]:
        args["workspace_path"] = os.path.join(output_path, "dense")

    if colmap_command in [
        "hierarchical_mapper",
        "mapper",
    ]:
        args["output_path"] = os.path.join(output_path, "sparse")

    if colmap_command in [
        "image_undistorter",
    ]:
        args["output_path"] = os.path.join(output_path, "dense")
        args["input_path"] = os.path.join(output_path, "sparse", "0")

    if colmap_command in [
        "stereo_fusion",
    ]:
        args["output_path"] = os.path.join(output_path, "dense", "fused.ply")

    if colmap_command in [
        "poisson_mesher",
        "delaunay_mesher",
    ]:
        args["input_path"] = os.path.join(output_path, "dense", "fused.ply")

    if colmap_command in [
        "poisson_mesher",
    ]:
        args["output_path"] = os.path.join(output_path, "dense", "poisson", "mesh.ply")

    if colmap_command in [
        "delaunay_mesher",
    ]:
        args["output_path"] = os.path.join(output_path, "dense", "delaunay", "mesh.ply")

    return args


def read_config(command_line_args) -> list:
    """
    read a yaml config file and return a bunch of commands
    """

    with open(command_line_args.config_file) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    assert os.path.exists(command_line_args.output_path)
    assert os.path.exists(os.path.join(command_line_args.output_path, "database"))

    commands = []
    for section in config:
        colmap_command = list(section.keys())
        assert len(colmap_command) == 1
        colmap_command = colmap_command[0]

        args = section[colmap_command]

        args = amend_args(
            colmap_command=colmap_command,
            args=args,
            image_path=command_line_args.image_path,
            output_path=command_line_args.output_path,
            database_path=os.path.join(command_line_args.output_path, "database", "database.db"),
        )

        args = [f"--{key} {value}" for key, value in args.items()]
        args = " ".join(args)

        command = f"colmap {colmap_command} {args}"
        commands.append(command)

    return commands

def run_commands(list_of_commands: list, log_file: str):
    """
    keep running commands until a non-zero exit code
    """

    assert os.path.isfile(log_file)
    assert ".json" in log_file

    with open(log_file, "r") as file:
        log = json.load(file)

    for i, c in enumerate(list_of_commands):
        print("=" * 40)
        print(f"{i+1}. {c}")
        print("=" * 40)

        starting_time = time.time()

        for path in execute(c):
            print(path, end="")

        ending_time = time.time()

        elapsed_time = ending_time - starting_time

        print("=" * 40)
        print(f"Command #{i} took {elapsed_time} seconds to complete")
        print("=" * 40)

        log.append({
            c: elapsed_time
        })

        with open(log_file, "w") as file:
            json.dump(log, file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a COLMAP workflow and record everything")
    parser.add_argument("--image_path",  type=str, help="path to folder with all the images", required=True)
    parser.add_argument("--config_file", type=str, help="path to yaml configuration file", required=True)
    parser.add_argument("--output_path", type=str, help="path where all output will be stored", required=True)
    parser.add_argument("--overwrite", type=bool, default=False, help="overwrite output path if it exists")
    parser.add_argument("--resume", type=bool, default=False, help="resume previous workflow without overwriting")
    args = parser.parse_args()

    # overwrite and resume cannot both be true
    if args.overwrite: assert not args.resume
    if args.resume: assert not args.overwrite

    create_output_path(args.output_path, args.overwrite, args.resume)

    commands = read_config(args)

    run_commands(commands, os.path.join(args.output_path, "log.json"))

    print("=" * 40)
    print("All commands run successfully!")
    print("=" * 40)



