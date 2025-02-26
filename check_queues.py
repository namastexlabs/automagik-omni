import pika
import sys

# RabbitMQ connection parameters
params = pika.URLParameters('amqp://namastex:Duassenha2024@192.168.112.131:5672')

try:
    # Connect to RabbitMQ
    print("Connecting to RabbitMQ...")
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    # Check the instance-specific queue
    instance_queue = 'nmstx-dev.messages.upsert'
    try:
        result = channel.queue_declare(queue=instance_queue, passive=True)
        print(f"Queue '{instance_queue}' exists with {result.method.message_count} messages and {result.method.consumer_count} consumers")
    except Exception as e:
        print(f"Error checking queue '{instance_queue}': {e}")
    
    # Check the application queue
    app_queue = 'evolution-api-nmstx-dev'
    try:
        result = channel.queue_declare(queue=app_queue, passive=True)
        print(f"Queue '{app_queue}' exists with {result.method.message_count} messages and {result.method.consumer_count} consumers")
    except Exception as e:
        print(f"Error checking queue '{app_queue}': {e}")
    
    # List all queues
    print("\nListing all queues:")
    try:
        # This is a management API feature, not available in pika directly
        print("Note: Cannot list all queues with pika directly. Use RabbitMQ Management UI.")
    except Exception as e:
        print(f"Error listing queues: {e}")
    
    # Close the connection
    connection.close()
    print("Connection closed")

except Exception as e:
    print(f"Error connecting to RabbitMQ: {e}")
    sys.exit(1) 