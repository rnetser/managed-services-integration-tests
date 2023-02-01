import pytest
from constants import TEST_RECORD


pytestmark = pytest.mark.mas_debezium


def test_kafka_topics(kafka_instance_client, kafka_topics, kafka_sa_acl, consumer_pod):
    """
    Test for managed kafka resources setup,
    usage and teardown via rhoas sdk
    """
    # Get consumed record from test topic via kcat pod
    kafka_event = consumer_pod.log()
    assert kafka_event.startswith(TEST_RECORD), "Failed to consume the correct record"
