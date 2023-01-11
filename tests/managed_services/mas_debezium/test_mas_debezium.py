import pytest


@pytest.mark.debezium_cdc
def test_kafka_topics(kafka_instance, kafka_instance_sa, kafka_topics):
    """
    Args:
        kafka_instance: Kafka cluster
        kafka_instance_sa: Service-account referring to kafka instance
                           with all producer/consumer privileges
        kafka_topics: Topics for kafka which correspond with mysql content
    """
    return
