from os import system
from glob import glob
import os
import argparse
from run import create_output_path, read_config, run_commands


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run multiple COLMAP workflows and record absolutely everything")

    default_vocab_tree_path = "/tmp/vocab_tree.bin"

    parser.add_argument("--image_path",  type=str,
                        help="path to folder with all the images", required=True)
    parser.add_argument("--input_path", type=str,
                        help="path to where all your yaml configuration files are", required=True)
    parser.add_argument("--output_path", type=str,
                        help="path where all output will be stored", required=True)

    parser.add_argument("--colmap_path", type=str,
                        default="colmap", help="path to your colmap executable")
    parser.add_argument("--vocab_tree_path", type=str,
                        default=default_vocab_tree_path, help="path to your colmap executable")

    args = parser.parse_args()

    assert os.path.exists(args.image_path) and os.path.isdir(args.image_path)
    assert os.path.exists(args.input_path) and os.path.isdir(args.input_path)
    assert os.path.exists(args.output_path) and os.path.isdir(args.output_path)

    assert os.path.exists(args.vocab_tree_path) and os.path.isfile(args.vocab_tree_path)

    if args.vocab_tree_path != default_vocab_tree_path and not os.path.exists(default_vocab_tree_path):
        os.symlink(args.vocab_tree_path, default_vocab_tree_path)

    configuration_files = glob(os.path.join(args.input_path, "*.yaml"))

    for config_file in configuration_files:
        configuration_name = config_file.split("/")[-1].replace(".yaml", "")
        print("Running configuration called '{}' found at '{}'".format(configuration_name, config_file))

        create_output_path(os.path.join(args.output_path, configuration_name), False, False)

        commands = read_config(config_file, args.image_path, os.path.join(args.output_path, configuration_name), args.colmap_path)

        try:
            run_commands(commands, os.path.join(args.output_path, configuration_name, "log.json"), verbose=False)
        except Exception as e:
            print("Failed to run the configuration file {} because of exception {}".format(
                configuration_name,
                e
            ))
            continue

        print("Completed configuration file {}".format(configuration_name))
