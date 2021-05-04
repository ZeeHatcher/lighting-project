## Setup
1. Create new thing object in AWS IoT Core, using [this guide](https://docs.aws.amazon.com/iot/latest/developerguide/create-iot-resources.html).
1. Create a new `.certs` directory in this folder.
1. Download AWS certificates and keys, and place them into the `.certs` directory.
1. Setup AWS SDK, using [this guide](https://docs.aws.amazon.com/iot/latest/developerguide/connecting-to-existing-device.html).
1. Setup required Python dependencies:
   1. Run `python3 -m pip install python-dotenv`
1. Copy `.env_example` into a new file called `.env`
1. Update values inside `.env` to work with your environment
