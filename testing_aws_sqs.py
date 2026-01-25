import boto3
import time

# use LocalStack to emulate aws
sqs = boto3.client(
    "sqs",
    endpoint_url="http://localhost:4566", 
    region_name="ap-southeast-2",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

QUEUE_NAME = "test-queue"

def run_test():
    print("creating queue ~~~")
    try:
        # create queue
        response = sqs.create_queue(QueueName=QUEUE_NAME)
        queue_url = response["QueueUrl"]
        print(f"Queue Created: {queue_url}")
    except Exception as e:
        print(f"Error creating queue: {e}")
        return

    print("Sending Messages...")
    sqs.send_message(QueueUrl=queue_url, MessageBody="Hello from Python!")
    sqs.send_message(QueueUrl=queue_url, MessageBody="Hello world")

    print("messages sent!")

    print("checking queue~~~")
    # Poll for messages

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=2  # Short wait
        )

        if "Messages" not in response:
            print("queue empty")
            break
            
        message = response["Messages"][0]
        print(f"received message: {message['Body']}")

        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )

        print("message deleted")



if __name__ == "__main__":
    run_test()
