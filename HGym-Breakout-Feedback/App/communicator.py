import asyncio, websockets, json, os, sys, pathlib, ssl
import json
from trial import get_trial_type
from multiprocessing import Process, Pipe
from s3upload import Uploader
import logging
import yaml

TRIAL_COUNTER_FILE = 'trial_counter.json'
ADDRESS = None # set desired IP for development 
PORT = 5000 # if port is changed here it must also be changed in Dockerfile
devEnv = False

logging.basicConfig(filename='server.log', level=logging.INFO)


def load_config():
    logging.info('Loading Config in communicator.py')
    with open('.trialConfig.yml', 'r') as infile:
        config = yaml.load(infile, Loader=yaml.FullLoader)
    logging.info('Config loaded in communicator.py')
    return config.get('trial')


def main():
    '''
    Check for command line arguement setting development environment.
    Start Websocket server at appropriate IP ADDRESS and PORT.
    '''
    global ADDRESS
    global PORT
    global devEnv

    config = load_config()
    configured_handler = lambda w, p: handler(w, p, config)
    init_trial_counter() # Initializes tracking for the current type of trial
    if len(sys.argv) > 1 and sys.argv[1] == 'dev':
        start_server = websockets.serve(configured_handler, ADDRESS, PORT)
        devEnv = True
    else:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain('fullchain.pem', keyfile='privkey.pem')
        start_server = websockets.serve(configured_handler, None, PORT, ssl=ssl_context)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

def init_trial_counter():
    with open(TRIAL_COUNTER_FILE, 'w+') as f:
        contents = {'total': 0}
        json.dump(contents, f)

def update_trial_counter(trial_type):
    # Open the TRIAL_COUNTER_FILE json file, and add one to the value
    # with key `trial_type`
    # If it does not exist, create it and set the value to 1
    with open(TRIAL_COUNTER_FILE, 'r') as f:
        data = json.load(f)

    if trial_type in data:
        data[trial_type] += 1
        data['total'] += 1
    else:
        data[trial_type] = 1
        if 'total' not in data:
            data['total'] = 1
        else:
            data['total'] += 1

    with open(TRIAL_COUNTER_FILE, 'w') as f:
        json.dump(data, f)

def get_trial_counter(trial_type=None):
    if not os.path.isfile(TRIAL_COUNTER_FILE):
        with open(TRIAL_COUNTER_FILE, 'w+') as f:
            contents = {'total': 0}
            if trial_type:
                contents[trial_type] = 0
            json.dump(contents, f)

    with open(TRIAL_COUNTER_FILE, 'r') as f:
        data = json.load(f)
    if trial_type:
        if trial_type in data:
            return data[trial_type]
        else:
            return 0
    return data
    
async def handler(websocket, path, config):
    '''
    On websocket connection, starts a new userTrial in a new Process.
    Then starts async listeners for sending and recieving messages.
    '''
    trial_counter = get_trial_counter('total')
    upPipe, downPipe = Pipe()
    trial_type = config['trial_types'][trial_counter]
    trial_type_counter = get_trial_counter(trial_type)
    trial_cls = get_trial_type(trial_type)
    logging.info('------- STARTING TRIAL WITH TYPE: ' + trial_type + ' ' + str(trial_counter) + ' -------')
    update_trial_counter(trial_type)
    userTrial = Process(target=trial_cls, args=(downPipe, trial_type_counter))
    userTrial.start()
    consumerTask = asyncio.ensure_future(consumer_handler(websocket, upPipe))
    producerTask = asyncio.ensure_future(producer_handler(websocket, upPipe))
    done, pending = await asyncio.wait(
        [consumerTask, producerTask],
        return_when = asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    await websocket.close()
    return

async def consumer_handler(websocket, pipe):
    '''
    Listener that passes messages directly to userTrial process via Pipe
    '''
    async for message in websocket:
        pipe.send(message)

async def producer_handler(websocket, pipe):
    '''
    Loop to call producer for messages to send from userTrial process.
    Note that asyncio.sleep() is required to make this non-blocking
    default sleep time is (0.01) which creates a maximum framerate of 
    just under 100 frames/s. For faster framerates decrease sleep time
    however be aware that this will affect the ability of the
    consumer_handler function to keep up with messages from the websocket
    and may cause poor performance if the web-client is sending a high volume
    of messages.
    '''
    done = False
    while True:
        done = await producer(websocket, pipe)
        await asyncio.sleep(0.01)
    return

async def producer(websocket, pipe):
    '''
    Check userTrial process pipe for messages to send to websocket.
    If userTrial is done, send final message to websocket and return
    True to tell calling functions that userTrial is complete.
    '''
    if pipe.poll():
        message = pipe.recv()
        if message == 'done':
            await websocket.send('done')
            return True
        elif 'upload' in message:
            await upload_to_s3(message)
        else:
            await websocket.send(message)
    return False

async def upload_to_s3(message):
    global devEnv
    logging.info(devEnv)
    if devEnv:
        logging.info('Dev set... Not uploading to s3.')
        return
    file = message['upload']['file']
    path = message['upload']['path']
    projectId = message['upload']['projectId']
    userId = message['upload']['userId']
    bucket =  message['upload']['bucket']
    compress = message['upload']['gzip']
    logging.info(f'Starting upload of {file} to s3...')
    Process(target=Uploader, args=(projectId, userId, file, path, bucket, compress)).start()

if __name__ == "__main__":
    main()
