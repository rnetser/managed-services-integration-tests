global config


api_server = "production"
aws_region = None
openshift_channel_group = "candidate"
aws_compute_machine_type = "m5.xlarge"
rosa_number_of_nodes = 2

# Add the above configuration to py_config config dict
for _dir in dir():
    val = locals()[_dir]
    if type(val) not in [bool, list, dict, str, int]:
        continue

    if _dir in ["encoding", "py_file"]:
        continue

    config[_dir] = locals()[_dir]  # noqa: F821
