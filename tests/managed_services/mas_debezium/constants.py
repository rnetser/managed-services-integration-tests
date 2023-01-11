# kafka service variables
KAFKA_NAME = "ms-kafka"
KAFKA_CLOUD_PROVIDER = "aws"
KAFKA_REGION = "us-east-1"
KAFKA_TIMEOUT_UNITS = 36
KAFKA_SA_NAME = "ms-kafka-sa"
KAFKA_TOPICS = [
    {"name": "avro", "cleanup_policy": "delete", "num_partitions": 1},
    {
        "name": "avro.inventory.addresses",
        "cleanup_policy": "delete",
        "num_partitions": 1,
    },
    {
        "name": "avro.inventory.customers",
        "cleanup_policy": "delete",
        "num_partitions": 1,
    },
    {"name": "avro.inventory.geom", "cleanup_policy": "delete", "num_partitions": 1},
    {"name": "avro.inventory.orders", "cleanup_policy": "delete", "num_partitions": 1},
    {
        "name": "avro.inventory.products",
        "cleanup_policy": "delete",
        "num_partitions": 1,
    },
    {
        "name": "avro.inventory.products_on_hand",
        "cleanup_policy": "delete",
        "num_partitions": 1,
    },
    {
        "name": "debezium-cluster-configs",
        "cleanup_policy": "compact",
        "num_partitions": 1,
    },
    {
        "name": "debezium-cluster-offsets",
        "cleanup_policy": "compact",
        "num_partitions": 1,
    },
    {
        "name": "debezium-cluster-status",
        "cleanup_policy": "compact",
        "num_partitions": 1,
    },
    {
        "name": "schema-changes.inventory",
        "cleanup_policy": "delete",
        "num_partitions": 1,
    },
]

# service-registry service variables

# MySQL variables

# Debezium variables
