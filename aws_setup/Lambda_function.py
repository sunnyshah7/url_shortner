import json
import boto3
import string
import random


# -----------------------------------------
# DynamoDB
# -----------------------------------------

dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table("urls")


# -----------------------------------------
# Base URL
# -----------------------------------------

BASE_URL = "https://jxyc2ymwoe.execute-api.ap-south-1.amazonaws.com"


# -----------------------------------------
# Generate Short Code
# -----------------------------------------

def generate_short_code(length=6):

    characters = string.ascii_letters + string.digits

    return ''.join(
        random.choices(characters, k=length)
    )


# -----------------------------------------
# Generate ID
# -----------------------------------------

# def generate_id():

#     return random.randint(1, 999999999)


# -----------------------------------------
# CREATE SHORT URL
# POST /shorten
# -----------------------------------------
def create_short_url(event):

    try:

        # ---------------------------------
        # Get request body
        # ---------------------------------

        body = json.loads(
            event.get("body", "{}")
        )

        # ---------------------------------
        # Get original URL
        # ---------------------------------

        original_url = body.get("original_url")

        if not original_url:

            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "original_url is required"
                })
            }

        # ---------------------------------
        # Check if URL already exists
        # ---------------------------------

        response = table.scan(
            FilterExpression="original_url = :url",
            ExpressionAttributeValues={
                ":url": original_url
            }
        )

        existing_urls = response.get(
            "Items",
            []
        )

        # ---------------------------------
        # URL already exists
        # ---------------------------------

        if existing_urls:

            existing_item = existing_urls[0]

            existing_short_code = existing_item.get(
                "short_code"
            )

            existing_short_url = (
                f"{BASE_URL}/{existing_short_code}"
            )

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "message": "URL already exists",
                    "original_url": original_url,
                    "short_code": existing_short_code,
                    "short_url": existing_short_url
                })
            }

        # ---------------------------------
        # URL does not exist
        # Generate new short code
        # ---------------------------------

        short_code = generate_short_code()

        # ---------------------------------
        # Save item to DynamoDB
        # ---------------------------------

        table.put_item(
            Item={
                "short_code": short_code,
                "original_url": original_url
            }
        )

        # ---------------------------------
        # Create short URL
        # ---------------------------------

        short_url = f"{BASE_URL}/{short_code}"

        # ---------------------------------
        # Return response
        # ---------------------------------

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Short URL created",
                "original_url": original_url,
                "short_code": short_code,
                "short_url": short_url
            })
        }

    except json.JSONDecodeError:

        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Invalid JSON request body"
            })
        }

    except Exception as e:

        print(
            "Create URL Error:",
            str(e)
        )

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Internal server error"
            })
        }
# -----------------------------------------
# GET ALL URLS
# GET /all
# -----------------------------------------

def get_all_urls():

    try:

        response = table.scan()

        urls = response.get("Items", [])

        result = []

        for url in urls:

            short_code = url.get("short_code")

            result.append({
                "original_url": url.get("original_url"),
                "short_code": short_code,
                "short_url": f"{BASE_URL}/{short_code}"
            })

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(result)
        }

    except Exception as e:

        print("Get All URLs Error:", str(e))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Internal server error"
            })
        }


# -----------------------------------------
# REDIRECT URL
# GET /{short_code}
# -----------------------------------------

def redirect_url(event, context):

    try:

        # Get short_code from API Gateway
        path_parameters = event.get(
            "pathParameters"
        ) or {}

        short_code = path_parameters.get(
            "short_code"
        )

        # Validate short code
        if not short_code:

            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "short_code is required"
                })
            }

        # Find URL in DynamoDB
        response = table.get_item(
            Key={
                "short_code": short_code
            }
        )

        # Get DynamoDB item
        item = response.get("Item")

        # Short code does not exist
        if not item:

            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Short URL not found"
                })
            }

        # Get original URL
        original_url = item.get(
            "original_url"
        )

        # Redirect user
        return {
            "statusCode": 302,
            "headers": {
                "Location": original_url
            },
            "body": ""
        }

    except Exception as e:

        print("Redirect Error:", str(e))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Internal server error"
            })
        }


# -----------------------------------------
# MAIN LAMBDA HANDLER
# -----------------------------------------

def lambda_handler(event, context):

    try:

        print(
            "Received event:",
            json.dumps(event)
        )

        # Get HTTP method
        method = event.get(
            "requestContext", {}
        ).get(
            "http", {}
        ).get(
            "method"
        )

        # Get path
        path = event.get(
            "rawPath",
            ""
        )

        print("Method:", method)
        print("Path:", path)


        # ---------------------------------
        # POST /shorten
        # ---------------------------------

        if method == "POST" and path == "/shorten":

            return create_short_url(event)


        # ---------------------------------
        # GET /all
        # ---------------------------------

        elif method == "GET" and path == "/all":

            return get_all_urls()



        # ---------------------------------
        # GET /{short_code}
        # ---------------------------------

        elif method == "GET":

            return redirect_url(
                event,
                context
            )
        

        # ---------------------------------
        # Delete /{short_code}
        # ---------------------------------


        elif method == "DELETE":
            return delete_url(event, context)

        # ---------------------------------
        # Route not found
        # ---------------------------------

        else:

            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Route not found"
                })
            }


    except Exception as e:

        print("Lambda Error:", str(e))

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Internal server error"
            })
        }

def delete_url(event, context):
    try:
        short_code = event.get("pathParameters", {}).get("short_code")
 
        if not short_code:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "short_code is required"
                })
            }
 
        response = table.delete_item(
            Key={
                "short_code": short_code
            },
            ReturnValues="ALL_OLD"
        )
 
        if "Attributes" not in response:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Short URL not found"
                })
            }
 
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "URL deleted successfully",
                "short_code": short_code
            })
        }
 
    except Exception as e:
        print("Error:", str(e))
 
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Internal server error"
            })
        }
 
 