import yaml
import subprocess
import argparse
import os
import shutil
import shlex
import time
import json
import pandas
import datetime
import tempfile


def delete_everything(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def execute(cmd):
    """
    taken from:
    https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
    """

    popen = subprocess.Popen(
        [cmd], stdout=subprocess.PIPE, shell=True, universal_newlines=True)
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
        assert not os.path.exists(
            output_path), "output folder already exists and won't be overwritten"

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
        "transitive_matcher",
        "sequential_matcher",
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
        "model_aligner",
    ]:
        args["output_path"] = os.path.join(output_path, "sparse", "0")
        args["input_path"] = os.path.join(output_path, "sparse", "0")

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

    ]:
        args["input_path"] = os.path.join(output_path, "dense", "fused.ply")
        args["output_path"] = os.path.join(
            output_path, "dense", "poisson", "mesh.ply")

    if colmap_command in [
        "delaunay_mesher",
    ]:
        args["input_path"] = os.path.join(output_path, "dense")
        args["output_path"] = os.path.join(output_path, "delaunay.ply")

    return args


def read_config(config_file, image_path, output_path, colmap_path) -> list:
    """
    read a yaml config file and return a bunch of commands
    """

    with open(config_file) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    assert os.path.exists(output_path)
    assert os.path.exists(os.path.join(
        output_path, "database"))

    if os.path.exists(image_path) and os.path.isfile(image_path) and image_path.endswith(".txt"):
        # create a temp folder in /tmp with symlinks to every image in the txt file
        with open(image_path, "r") as image_list_file:
            image_list = image_list_file.readlines()
        
        assert len(image_list) > 0

        image_path = "/tmp/colmap_images"

        if os.path.exists(image_path):
            delete_everything(image_path)
        else:
            os.mkdir(image_path)

        for image in image_list:
            image = image.strip()
            assert os.path.isabs(image)
            assert os.path.exists(image) and os.path.isfile(image)
            _, tail = os.path.split(image)
            os.symlink(image, os.path.join(image_path, tail))


    commands = []
    for section in config:
        colmap_command = list(section.keys())
        assert len(colmap_command) == 1
        colmap_command = colmap_command[0]

        args = section[colmap_command]

        args = amend_args(
            colmap_command=colmap_command,
            args=args,
            image_path=image_path,
            output_path=output_path,
            database_path=os.path.join(
                output_path, "database", "database.db"),
        )

        args = [f"--{key} {value}" for key, value in args.items()]
        args = " ".join(args)

        command = f"{colmap_path} {colmap_command} {args}"
        commands.append(command)

    return commands


def run_commands(list_of_commands, log_file, verbose=True):
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
        command_output = ""
        for path in execute(c):
            if verbose:
                print(path, end="")
            command_output += path
        ending_time = time.time()
        elapsed_time = ending_time - starting_time

        print("=" * 40)
        print(f"Command #{i} took {elapsed_time} seconds to complete")
        print("=" * 40)

        log.append({
            "command": c,
            "elapsed_time": elapsed_time,
            "output": command_output,
        })

        with open(log_file, "w") as file:
            json.dump(log, file)


if __name__ == "__main__":
    default_vocab_tree_path = "/tmp/vocab_tree.bin"
    default_georegistration_path = "/tmp/georegistration.txt"

    parser = argparse.ArgumentParser(
        description="Run a COLMAP workflow and record everything")
    parser.add_argument("--image_path",  type=str,
                        help="path to folder with all the images, or a text file containing absolute paths to images", required=True)
    parser.add_argument("--config_file", type=str,
                        help="path to yaml configuration file", required=True)
    parser.add_argument("--output_path", type=str,
                        help="path where all output will be stored", required=True)
    parser.add_argument("--overwrite", type=bool, default=False,
                        help="overwrite output path if it exists")
    parser.add_argument("--resume", type=bool, default=False,
                        help="resume previous workflow without overwriting")
    parser.add_argument("--colmap_path", type=str,
                        default="colmap", help="path to your colmap executable")
    parser.add_argument("--vocab_tree_path", type=str,
                        default=default_vocab_tree_path, help="path to the vocabulary tree binary")
    parser.add_argument("--georegistration", type=str,
                        default=default_georegistration_path, help="path to a text file with gps coordinates for every image")

    args = parser.parse_args()

    # overwrite and resume cannot both be true
    if args.overwrite:
        assert not args.resume
    if args.resume:
        assert not args.overwrite

    assert os.path.exists(args.vocab_tree_path) and os.path.isfile(args.vocab_tree_path)
    if args.vocab_tree_path != default_vocab_tree_path:
        if os.path.exists(default_vocab_tree_path):
            os.remove(default_vocab_tree_path)
        os.symlink(args.vocab_tree_path, default_vocab_tree_path)

    assert os.path.exists(args.georegistration) and os.path.isfile(args.georegistration)
    if args.georegistration != default_georegistration_path:
        if os.path.exists(default_georegistration_path):
            os.remove(default_georegistration_path)
        os.symlink(args.georegistration, default_georegistration_path)

    create_output_path(args.output_path, args.overwrite, args.resume)

    commands = read_config(args.config_file, args.image_path, args.output_path, args.colmap_path)

    run_commands(commands, os.path.join(args.output_path, "log.json"), verbose=True)

    print("=" * 40)
    print("All commands run successfully!")
    print("=" * 40)

