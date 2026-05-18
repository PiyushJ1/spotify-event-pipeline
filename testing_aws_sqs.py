import boto3
import os, sys
from dotenv import load_dotenv

load_dotenv()


# create sqs instance
sqs = boto3.client(
    "sqs",
    region_name="ap-southeast-2",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_ACCESS_SECRET_KEY"),
)


def run_test():
    print("creating queue ~~~")
    # try:
    #     # create queue
    #     response = sqs.create_queue(QueueName=QUEUE_NAME)
    #     queue_url = response["QueueUrl"]
    #     print(f"Queue Created: {queue_url}")
    # except Exception as e:
    #     print(f"Error creating queue: {e}")
    #     return

    queue_url = "https://sqs.ap-southeast-2.amazonaws.com/555379836133/spotify-queue"
    print("Sending Messages...")
    sqs.send_message(QueueUrl=queue_url, MessageBody="Hello from Python!")
    sqs.send_message(QueueUrl=queue_url, MessageBody="Hello world")

    print("messages sent!")

    print("checking queue~~~")
    # Poll for messages

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=1  # Short wait
        )

        if "Messages" not in response:
            print("queue empty")
            break

        message = response["Messages"][0]
        print(f"received message: {message['Body']}")

        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])

        print("message deleted")


if __name__ == "__main__":
    run_test()
