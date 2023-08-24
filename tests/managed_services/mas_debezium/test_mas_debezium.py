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
        assert not missing_topics, (
            f"Missing kafka topics: {missing_topics}, expected topics:"
            f" {KAFKA_TOPICS_LIST}"
        )

    def test_kafka_record_in_consumer_pod(
        self,
        kafka_instance_ready,
        first_kafka_topic_name,
        kafka_record,
        kafka_instance_sa,
        kafka_sa_acl_binding,
        consumer_pod,
    ):
        # Get consumed record from test topic via kcat pod
        consumed_event = consumer_pod.execute(
            container=consumer_pod.name,
            command=shlex.split(
                s=(
                    f"kcat -b {kafka_instance_ready.bootstrap_server_host} "
                    "-X sasl.mechanisms=PLAIN "
                    "-X security.protocol=SASL_SSL "
                    f"-X sasl.username={kafka_instance_sa.id} "
                    f"-X sasl.password={kafka_instance_sa.secret} "
                    f"-t {first_kafka_topic_name} -C -e"
                )
            ),
        )
        assert consumed_event.strip("\n") == kafka_record, (
            "Failed to consume the correct record. Existing Kafka"
            f" event:\n{consumed_event}"
        )
