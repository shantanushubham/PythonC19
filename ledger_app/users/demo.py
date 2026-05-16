from asgiref.sync import sync_to_async
import requests
import httpx
from users.models import User

DUMMY_URL = "https://airtribe.live/abc"


async def test_function(request):
  data = await httpx.get(DUMMY_URL) # 2 seconds
  return data.json()


async def get_user(request):
  user = await sync_to_async(User.objects.get(phone_number="9876543210"))


# The job is given to a different thread, freeing the worker thread so that
# it can cater to other requests.
# When the job finishes, the data is returned back to the original thread that called it.
# This happens internally using multithreading in python.


# There is a Main Thread
# Main Thread will be running test_function
# The main thread will wait until line 4 finishes.
# Return the data

# In Backend-systems, There is something called as a Worker
# A worker is basically like a sub-process that can handle threads
# By Default - 1 incoming request completely blocks 1 worker.
# Lets assume you have 5 workers, and in a span of 2 seconds, you received 5 requests.
# The moment 6th request comes, it will have to wait for at least 1 worker to be free.

# What if, 1 worker can handle more than 1 incoming request?
# This is possible because of ASGI