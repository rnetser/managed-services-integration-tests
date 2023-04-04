import pytest

from utilities.constants import KAFKA_TOPICS_LIST
from utilities.test_utils import kafka_record_in_consumer_pod_test


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
        self,
        kafka_instance_ready,
        first_kafka_topic_name,
        kafka_record,
        kafka_instance_sa,
        kafka_sa_acl_binding,
        consumer_pod,
    ):
        kafka_record_in_consumer_pod_test(
            consumer_pod=consumer_pod,
            kafka_instance_ready=kafka_instance_ready,
            kafka_instance_sa=kafka_instance_sa,
            first_kafka_topic_name=first_kafka_topic_name,
            kafka_record=kafka_record,
        )
