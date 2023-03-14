import shlex

import pytest
from constants import KAFKA_TOPICS_LIST


pytestmark = pytest.mark.mas_debezium


class TestDebezium:
    def test_create_kafka_topics(self, kafka_topics):
        created_kafka_topics_names = [topic_dict.name for topic_dict in kafka_topics]
        missing_topics = [
            topic
            for topic in KAFKA_TOPICS_LIST
            if topic not in created_kafka_topics_names
        ]
        assert (
            not missing_topics
        ), f"Missing kafka topics: {missing_topics}, expected topics: {KAFKA_TOPICS_LIST}"

    def test_kafka_record_in_consumer_pod(
        self, kafka_record, kafka_sa_acl_binding, consumer_pod
    ):
        # Get consumed record from test topic via kcat pod
        consumed_event = consumer_pod.execute(
            container=consumer_pod.name,
            command=shlex.split(
                s=f"kcat -b {consumer_pod.kafka_bootstrap_url} "
                "-X sasl.mechanisms=PLAIN "
                "-X security.protocol=SASL_SSL "
                f"-X sasl.username={consumer_pod.kafka_sa_client_id} "
                f"-X sasl.password={consumer_pod.kafka_sa_client_secret} "
                f"-t {consumer_pod.kafka_test_topic} -C -e"
            ),
        )
        assert (
            consumed_event.strip("\n") == kafka_record
        ), f"Failed to consume the correct record. Existing Kafka event:\n{consumed_event}"
