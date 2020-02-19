import yaml
import subprocess
import argparse
import os
import shutil
import shlex
import time
import json
import jtop
import pandas
import flatten_dict
import datetime
import pprint



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read in and pretty print a COLMAP workflow log")
    parser.add_argument("--json_file", type=str, help="path to your log.json file", required=True)
    parser.add_argument("--jetson", type=str, default="all", help="comma seperated string of all the columns you need")
    args = parser.parse_args()


    assert os.path.isfile(args.json_file)

    jetson_args = None
    if args.jetson != "all":
        if "," in args.jetson:
            jetson_args = args.jetson.split(",")
        else:
            jetson_args = [args.jetson]


    with open(args.json_file, "r") as file:
        logs = json.load(file)

    column_names = []

    total_seconds = 0.0

    for line in logs:
        print("=" * 40)
        print(f"Command: {line['command']}")
        print(f"Time elapsed: {line['elapsed_time'] / 60.0} minutes \n")
        print("=" * 40)

        total_seconds += line['elapsed_time']
        
        df = pandas.DataFrame.from_dict(line['jetson_stats'])

        df.index = pandas.to_datetime(df.index, unit='s', origin='unix', utc=True)
        #df = df.resample('1T').mean().interpolate()
        #df = df.mean()

        # first_time_stamp = float(df.index[0])
        # df.index = [int(float(x) - first_time_stamp) for x in df.index]
        # df.index.name = "seconds"
        column_names = list(df.columns)

        if jetson_args is not None:
            df = df[jetson_args]

        print(df.mean())

        print("=" * 40)
        print("\n" * 4)

    print("List of all Jetson log columns: \n")
    for c in column_names:
        print(f"- {c}")

    print("\n" * 4)

    print(f"Total time in hours was: {total_seconds / (60.0 * 60.0)}")






