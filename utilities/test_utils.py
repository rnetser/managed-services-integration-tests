import logging
import shlex


LOGGER = logging.getLogger(__name__)


def kafka_record_in_consumer_pod_test(
    consumer_pod,
    kafka_instance_ready,
    kafka_instance_sa,
    first_kafka_topic_name,
    kafka_record,
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
