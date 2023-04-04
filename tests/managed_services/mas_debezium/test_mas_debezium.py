import shlex

import pytest

from utilities.test_utils import create_kafka_topics_test


pytestmark = pytest.mark.mas_debezium


class TestDebezium:
    def test_create_kafka_topics(self, kafka_topics):
        create_kafka_topics_test(created_kafka_topics=kafka_topics)

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
                s=f"kcat -b {kafka_instance_ready.bootstrap_server_host} "
                "-X sasl.mechanisms=PLAIN "
                "-X security.protocol=SASL_SSL "
                f"-X sasl.username={kafka_instance_sa.id} "
                f"-X sasl.password={kafka_instance_sa.secret} "
                f"-t {first_kafka_topic_name} -C -e"
            ),
        )
        assert (
            consumed_event.strip("\n") == kafka_record
        ), f"Failed to consume the correct record. Existing Kafka event:\n{consumed_event}"
