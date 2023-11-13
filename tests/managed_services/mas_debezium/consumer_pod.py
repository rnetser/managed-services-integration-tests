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

    def to_dict(self):
        super().to_dict()

        self.res.update({
            "spec": {
                "containers": [
                    {
                        "name": self.name,
                        "image": self.consumer_image,
                        "command": shlex.split(s="sleep 1d"),
                    }
                ],
            }
        })
