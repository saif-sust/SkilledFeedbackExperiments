import numpy, json, shortuuid, time, base64, yaml, logging
import _pickle as cPickle
from PIL import Image
from io import BytesIO
from agent import Agent, ReplayAgent
import os



def load_config():
    logging.info('Loading Config in trial.py')
    with open('.trialConfig.yml', 'r') as infile:
        config = yaml.load(infile, Loader=yaml.FullLoader)
    logging.info('Config loaded in trial.py')
    return config.get('trial')

def get_trial_type(trial_type):
    return TRIAL_TYPE_MAPPING[trial_type]

class Trial():
    def __init__(self, pipe, trial_idx=0):
        self.config = load_config()
        self.pipe = pipe
        self.frameId = 0
        self.humanAction = 0
        self.episode = 0
        self.done = False
        self.play = False
        self.record = []
        self.nextEntry = {}
        self.trialId = shortuuid.uuid()
        self.outfile = None
        self.framerate = self.config.get('startingFrameRate', 30)
        self.userId = None
        self.projectId = self.config.get('projectId')
        self.filename = None
        self.path = None
        self.trial_type = TYPE_TRIAL_MAPPING[type(self)]
        self.trial_idx = trial_idx
        if self.config.get('advancedActionSpace') is not None:
            self.active_keys = set([])
            self.valid_keys = set(self.config.get('validKeys'))
            action_keys = self.config.get('advancedActionSpace')
            self.key_act_map = {frozenset(key_set): i for i, key_set in enumerate(action_keys)}
            self.humanAction = self.key_act_map.get(None, 0)
            self.action_space_type = 'advanced'
        elif self.config.get('continuousActionSpace') is not None:
            self.active_keys = set([])
            self.valid_keys = set(self.config.get('validKeys'))
            self.key_act_map = {frozenset(k) if k is not None else None: v \
                for k, v in self.config.get('continuousActionSpace')}
            self.humanAction = self.key_act_map.get(None, 0)
            self.action_space_type = 'advanced'
        else:
            self.action_space_type = 'simple'

        print(self.humanAction)
        self.start()
        self.run()

    def start(self):
        '''
        Call the function in the Agent/Environment combo required to start 
        a trial. By default passes the environment name that will be passed
        to gym.make(). 
        By default this expects the openAI Gym Environment object to be
        returned. 
        '''
        self.agent = Agent()
        self.agent.start(self.config.get('game'), self.config.get('frameskip', 1), self.config.get('maxEpisodeFrames', -1))

    def run(self):
        '''
        This is the main event controlling function for a Trial. 
        It handles the render-step loop
        '''
        while not self.done:
            message = self.check_message()
            if message:
                self.handle_message(message)
            if self.play:
                render = self.get_render()
                self.send_render(render)
                self.take_step()
            time.sleep(1/self.framerate)

    def reset(self):
        '''
        Resets the OpenAI gym environment to start a new episode.
        By default this function will create a new log file for every
        episode, if the intention is to log only full trials then
        comment the 3 lines below contianing self.outfile and 
        self.create_file.
        '''
        if self.check_trial_done():
            self.end()
        else:
            self.agent.reset()
            if self.outfile:
                self.outfile.close()
                if self.config.get('s3upload'):
                    self.pipe.send({'upload':{
                        'projectId': self.projectId,
                        'userId': self.userId,
                        'file': self.filename,
                        'path': self.path,
                        'bucket': self.config.get('bucket'),
                        'gzip': True}})
            self.create_file()
            self.episode += 1

    def check_trial_done(self):
        '''
        Checks if the trial has been completed and can be quit. Add conditions
        as required.
        '''
        return self.episode >= self.config.get('maxEpisodes', 20)

    def end(self):
        '''
        Closes the environment through the agent, closes any remaining outfile
        and sends the 'done' message to the websocket pipe. If logging the 
        whole trial memory in self.record, uncomment the call to self.save_record()
        to write the record to file before closing.
        '''
        self.pipe.send('done')
        self.agent.close()
        if self.config.get('dataFile') == 'trial':
            self.save_record()
        if self.outfile:
            self.outfile.close()
            self.pipe.send({'upload':{
                'projectId': self.projectId,
                'userId': self.userId,
                'file': self.filename,
                'path': self.path,
                'bucket': self.config.get('bucket'),
                'gzip': True}})
        
        self.play = False
        self.done = True

    def check_message(self):
        '''
        Checks pipe for messages from websocket, tries to parse message from
        json. Retruns message or error message if unable to parse json.
        Expects some poorly formatted or incomplete messages.
        '''
        if self.pipe.poll():
            message = self.pipe.recv()
            try:
                message = json.loads(message)
            except:
                message = {'error': 'unable to parse message', 'frameId': self.frameId}
            return message
        return None

    def handle_message(self, message:dict):
        '''
        Reads messages sent from websocket, handles commands as priority then 
        actions. Logs entire message in self.nextEntry
        '''
        logging.info('Message: ' + str(message))
        if not self.userId and 'userId' in message:
            self.userId = message['userId'] or f'user_{shortuuid.uuid()}'
            self.send_ui()
            self.reset()
            render = self.get_render()
            self.send_render(render)
        if 'command' in message and message['command']:
            self.handle_command(message['command'])
        elif 'changeFrameRate' in message and message['changeFrameRate']:
            self.handle_framerate_change(message['changeFrameRate'])
        elif 'action' in message and message['action'] and self.action_space_type == 'simple':
            self.handle_action(message['action'])
        elif 'KeyboardEvent' in message and self.action_space_type == 'advanced':
            self.handle_advanced_action(message['KeyboardEvent'])
        self.update_entry(message)

    def handle_command(self, command:str):
        '''
        Deals with allowable commands from user. To add other functionality
        add commands.
        '''
        command = command.strip().lower()
        if command == 'start':
            self.play = True
        elif command == 'stop':
            self.end()
        elif command == 'reset':
            self.reset()
        elif command == 'pause':
            self.play = False
        elif command == 'requestUI':
            self.send_ui()

    def handle_framerate_change(self, change:str):
        '''
        Changes the framerate in either increments of step, or to a requested 
        value within a minimum and maximum bound.
        '''
        if not self.config.get('allowFrameRateChange'):
            return

        step = self.config.get('frameRateStepSize', 5)
        minFR = self.config.get('minFrameRate', 1)
        maxFR = self.config.get('maxFrameRate', 90)
        change = change.strip().lower()
        if change == 'faster' and self.framerate + step < maxFR:
            self.framerate += step
        elif change == 'slower' and self.framerate - step > minFR:
            self.framerate -= step
        else:
            try:
                requested = int(change)
                if requested > minFR and requested < maxFR:
                    self.framerate = requested
            except:
                pass


    def handle_action(self, action:str):
        '''
        Translates action to int and resets action buffer if action !=0
        '''
        action = action.strip().lower()
        actionSpace = self.config.get('actionSpace')
        if action in actionSpace:
            actionCode = actionSpace.index(action)
        else:
            actionCode = 0
        self.humanAction = actionCode

    def handle_advanced_action(self, event:dict):
        '''
        Translates action to int and resets action buffer if action !=0
        '''
        if 'KEYDOWN' in event:
            if self.valid_keys is None or event['KEYDOWN'][0] in self.valid_keys:
                self.active_keys.add(event['KEYDOWN'][0])
        if 'KEYUP' in event:
            if event['KEYUP'][0] in self.active_keys:
                self.active_keys.remove(event['KEYUP'][0])

        action_code = self.key_act_map.get(frozenset(self.active_keys))
        if action_code is None:
            action_code = self.key_act_map.get(None, 0)
        self.humanAction = action_code
   
    def update_entry(self, update_dict:dict):
        '''
        Adds a generic dictionary to the self.nextEntry dictionary.
        '''
        self.nextEntry.update(update_dict)

    def get_render(self):
        '''
        Calls the Agent/Environment render function which must return a npArray.
        Translates the npArray into a jpeg image and then base64 encodes the 
        image for transmission in json message.
        '''
        render = self.agent.render()
        try:
            img = Image.fromarray(render)
            fp = BytesIO()
            img.save(fp,'JPEG')
            frame = base64.b64encode(fp.getvalue()).decode('utf-8')
            fp.close()
        except: 
            raise TypeError("Render failed. Is env.render('rgb_array') being called\
                            With the correct arguement?")
        self.frameId += 1
        return {'frame': frame, 'frameId': self.frameId}

    def send_render(self, render:dict):
        '''
        Attempts to send render message to websocket
        '''
        try: 
            self.pipe.send(json.dumps(render))
        except:
            raise TypeError("Render Dictionary is not JSON serializable")

    def send_ui(self):
        defaultUI = ['left','right','up','down','start','pause']
        try:
            ui_settings = self.config.get(self.trial_type + '_ui', defaultUI)
            self.pipe.send(json.dumps({'UI': ui_settings}))
        except:
            raise TypeError("Render Dictionary is not JSON serializable")

    def take_step(self):
        '''
        Expects a dictionary return with all the values that should be recorded.
        Records return and saves all memory associated with this setp.
        Checks for DONE from Agent/Env
        '''
        envState = self.agent.step(self.humanAction)
        self.update_entry(envState)
        self.save_entry()
        if envState['done']:
            self.reset()

    def save_entry(self):
        '''
        Either saves step memory to self.record list or pickles the memory and
        writes it to file, or both.
        Note that observation and render objects can get large, an episode can
        have several thousand steps, holding all the steps for an episode in 
        memory can cause performance issues if the os needs to grow the heap.
        The program can also crash if the Server runs out of memory. 
        It is recommended to write each step to file and not maintain it in
        memory if the full observation is being saved.
        comment/uncomment the below lines as desired.
        '''
        if self.config.get('dataFile') == 'trial':
            self.record.append(self.nextEntry)
        else:
            cPickle.dump(self.nextEntry, self.outfile)
            self.nextEntry = {}

    def save_record(self):
        '''
        Saves the self.record object to file. Is only called if uncommented in
        self.end(). To record full trial records a line must also be uncommented
        in self.save_entry() and self.create_file()
        '''
        cPickle.dump(self.record, self.outfile)
        self.record = []

    def create_file(self):
        '''
        Creates a file to record records to. comment/uncomment as desired 
        for episode or full-trial logging.
        '''
        if self.config.get('dataFile') == 'trial':
            filename = f'trial_{self.userId}'
        else:
            filename = f'episode_{self.episode}_user_{self.userId}'
        path = 'Trials/'+filename
        self.outfile = open(path, 'ab')
        self.filename = filename
        self.path = path

TRIAL_DATA_DIR = 'ReplayData'

class FeedbackTrial(Trial):
    def __init__(self, pipe, trial_idx=0):
        self.human_feedback = 0
        super().__init__(pipe, trial_idx)

    def _get_trial_path(self, trial_idx):
        exp_names = os.listdir(TRIAL_DATA_DIR)
        if len(exp_names) != 1:
            raise ValueError(f'Expected 1 experiment, got {len(exp_names)}: {exp_names}')
        exp_name = exp_names[0]
        return f'{TRIAL_DATA_DIR}/{exp_name}/replay_data_{trial_idx}'

    def start(self):
        trial_path = self._get_trial_path(self.trial_idx)
        logging.info(f'Starting feedback trial {self.trial_idx} with path {trial_path}')

        self.agent = ReplayAgent()
        self.agent.start(trial_path) # self.config.get('game'))

    def take_step(self):
        '''
        Expects a dictionary return with all the values that should be recorded.
        Records return and saves all memory associated with this setp.
        Checks for DONE from Agent/Env
        '''
        envState = self.agent.step(self.humanAction)
        self.update_entry({'step': envState['step'], 'feedback': self.human_feedback})
        self.human_feedback = 0
        self.save_entry()
        if envState['done']:
            self.reset()
            
    def handle_command(self, command:str):
        '''
        Deals with allowable commands from user. To add other functionality
        add commands.
        '''
        # Call parent function and then check additional commands
        super().handle_command(command)
        command = command.strip().lower()
        if command == 'good':
            self.human_feedback = 1
        elif command == 'bad':
            self.human_feedback = -1

TRIAL_TYPE_MAPPING = {
    'play_game': Trial,
    'give_feedback': FeedbackTrial
}

TYPE_TRIAL_MAPPING = {v: k for k, v in TRIAL_TYPE_MAPPING.items()}