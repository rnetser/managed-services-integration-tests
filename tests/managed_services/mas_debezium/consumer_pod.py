import shlex

from ocp_resources.constants import TIMEOUT_4MINUTES
from ocp_resources.pod import Pod


class ConsumerPod(Pod):
    def __init__(
        self,
        name=None,
        namespace=None,
        client=None,
        teardown=True,
        privileged_client=None,
        yaml_file=None,
        consumer_image=None,
        kafka_bootstrap_url=None,
        kafka_sa_client_id=None,
        kafka_sa_client_secret=None,
        kafka_test_topic=None,
        delete_timeout=TIMEOUT_4MINUTES,
        **kwargs,
    ):
        super().__init__(
            name=name,
            namespace=namespace,
            client=client,
            teardown=teardown,
            privileged_client=privileged_client,
            yaml_file=yaml_file,
            delete_timeout=delete_timeout,
            **kwargs,
        )
        self.consumer_image = consumer_image
        self.kafka_bootstrap_url = kafka_bootstrap_url
        self.kafka_sa_client_id = kafka_sa_client_id
        self.kafka_sa_client_secret = kafka_sa_client_secret
        self.kafka_test_topic = kafka_test_topic

    def to_dict(self):
        super().to_dict()

        self.res.update(
            {
                "spec": {
                    "containers": [
                        {
                            "name": self.name,
                            "image": self.consumer_image,
                            "command": shlex.split(s="sleep 1d"),
                        }
                    ],
                }
            }
        )
