import pytest
from constants import TEST_RECORD


pytestmark = pytest.mark.mas_debezium


class TestDebezium:
    def test_kafka_topics(
        self, kafka_instance_client, kafka_topics, kafka_sa_acl, consumer_pod
    ):
        """
        Test for managed kafka resources setup,
        usage and teardown via rhoas sdk
        """
        # Get consumed record from test topic via kcat pod
        kafka_log = consumer_pod.log()
        assert kafka_log.startswith(
            TEST_RECORD
        ), f"Failed to consume the correct record. Existing Kafka event:\n{kafka_log}"
