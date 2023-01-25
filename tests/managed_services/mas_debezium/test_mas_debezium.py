import shlex

import pytest
from constants import CONSUMER_POD, PARTITION
from rhoas_kafka_instance_sdk.api import records_api
from rhoas_kafka_instance_sdk.model.record import Record


pytestmark = pytest.mark.mas_debezium


def test_kafka_topics(kafka_instance_client, kafka_topics, consumer_pod):
    """
    Test for managed kafka resources setup,
    usage and teardown via rhoas sdk
    """
    # Produce to avro.inventory.customers topic
    records_api_client = records_api.RecordsApi(api_client=kafka_instance_client)
    topic_name = "avro.inventory.customers"
    record_msg = "This is a topic test record"
    record = Record(value=record_msg, partition=PARTITION)
    records_api_client.produce_record(topic_name=topic_name, record=record)

    # Consume from avro.inventory.customers topic using kcat
    consume_command = (
        "kcat -b $BOOTSTRAP_SERVER "
        "-X sasl.mechanisms=PLAIN "
        "-X security.protocol=SASL_SSL "
        '-X sasl.username="$CLIENT_ID" '
        '-X sasl.password="$CLIENT_SECRET" '
        "-t avro.inventory.customers -C -e"
    )
    # TODO: command execution fails at args parsing
    kafka_event = consumer_pod.execute(
        command=shlex.split(s=consume_command),
        container=CONSUMER_POD,
    )
    assert kafka_event == record_msg, "Failed to consume the correct record"
