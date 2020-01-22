# COLMAP Runner

## Features

- Run a typical COLMAP workflow from a config file
- Log output, time taken, and resource utilization of each command

## How to run

```
git clone https://github.com/KhaledSharif/colmap-runner.git
cd colmap-runner
python3 ./run.py --image_path ../graham-hall/exterior --config_file ./config/light.yaml --output_path ./output
```

## Output directory structure

```
root@jetson:/output # tree -L 2
.
├── database
│   └── database.db
├── dense
│   ├── fused.ply
│   ├── fused.ply.vis
│   ├── images
│   ├── run-colmap-geometric.sh
│   ├── run-colmap-photometric.sh
│   ├── sparse
│   └── stereo
├── log.json
└── sparse
    ├── 0
    ├── 1
    └── 2
```