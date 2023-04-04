from utilities.constants import KAFKA_TOPICS_LIST


def create_kafka_topics_test(
    created_kafka_topics, expected_kafka_topics=KAFKA_TOPICS_LIST
):
    created_kafka_topics_names = [
        topic_dict.name for topic_dict in created_kafka_topics
    ]
    missing_topics = [
        topic
        for topic in expected_kafka_topics
        if topic not in created_kafka_topics_names
    ]
    assert (
        not missing_topics
    ), f"Missing kafka topics: {missing_topics}, expected topics: {expected_kafka_topics}"
