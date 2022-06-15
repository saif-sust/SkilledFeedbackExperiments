import os
import glob
import json
import gzip
import pickle
from collections import namedtuple


PlayStep = namedtuple('PlayStepData', ['action', 'obs', 'raw_obs', 'reward', 'done'])
FeedbackStep = namedtuple('FeedbackStepData', ['feedback', 'done'])

SURVEY_ONE_MAPPING = {
    'experience': 'ai_experience',
    'game': 'gen_game_play_freq',
    'age': 'age',
    'education': 'education',
    'game_exp': 'this_game_experience',
    'game_skill': 'this_game_skill',
    'comment': 'before_comment'
}

SURVEY_TWO_MAPPING = {
    'understand': 'understand_game',
    'understandf': 'understand_feedback',
    'comment': 'after_comment'
}


class Participant():
    def __init__(self, uid, user_data_path=None, play_data_paths=None,
                 feedback_data_paths=None, experiment_id=None):
        self.uid = uid
        self.user_data_path = user_data_path
        self.play_data_paths = play_data_paths
        self.feedback_data_paths = feedback_data_paths
        self.experiment_id = experiment_id
        self.user_data = None

    def get_survey_data(self):
        if self.user_data is None and self.user_data_path is not None:
            self._parse_user_data()
        return self.user_data

    def get_play_data(self, idx=None):
        if idx is None:
            replay_data = []
            for i in range(len(self.play_data_paths)):
                replay_data.append(self.get_play_data(i))
            return replay_data

        path = self.play_data_paths[idx]
        # Unzip the file and load the pickled data
        steps = []
        with gzip.open(path, 'rb') as f:
            while f.peek(1):
                data = pickle.load(f)
                steps.append(data)
        if len(steps) == 1:
            steps = steps[0]

        transitions = []
        for step in steps:
            # Action may not be recorded in earlier versions
            transitions.append(PlayStep(
                step.get('action'),
                step['observation'],
                step.get('raw_observation', step['observation']),
                step['reward'],
                step['done']))

        return transitions

    def get_feedback_data(self, idx=None):
        if idx is None:
            feedback_data = []
            for i in range(len(self.feedback_data_paths)):
                feedback_data.append(self.get_feedback_data(i))
            return feedback_data

        path = self.feedback_data_paths[idx]
        # Unzip the file and load the pickled data
        steps = []
        with gzip.open(path, 'rb') as f:
            while f.peek(1):
                data = pickle.load(f)
                steps.append(data)
        if len(steps) == 1:
            steps = steps[0]

        transitions = []
        for step in steps:
            # Action may not be recorded in earlier versions
            transitions.append(FeedbackStep(
                step['feedback'], step['done']))

        return transitions

    def _parse_user_data(self):
        with open(self.user_data_path, 'r') as f:
            user_data = json.load(f)

        self.user_data = {}
        for request in user_data['requests']:
            body = request['body']
            if body is None:
                continue
            else:
                body = json.loads(body)
                
            if 'experience' in body:
                for key, value in body.items():
                    self.user_data[SURVEY_ONE_MAPPING[key]] = value
            elif 'understand' in body:
                for key, value in body.items():
                    self.user_data[SURVEY_TWO_MAPPING[key]] = value

    def __repr__(self):
        if self.experiment_id is None:
            return '<Participant uid={}>'.format(self.uid)
        return '<Participant uid={} experiment_id={}>'.format(self.uid, self.experiment_id)

def load_participant_data(data_path='data/trials'):
    game_paths = glob.glob('{}/*'.format(data_path))
    participants = {}
    for game_path in game_paths:
        experiment_id = os.path.basename(game_path)
        folders = os.listdir(game_path)
        if 'Users' in folders:
            users_dir = os.path.join(game_path, 'Users')
            for user_file in os.listdir(users_dir):
                participant = Participant(
                    user_file,
                    user_data_path=os.path.join(users_dir, user_file),
                    experiment_id=experiment_id)
                participants[participant.uid] = participant
        if 'Trials' in folders:
            trials_dir = os.path.join(game_path, 'Trials')
            for trial_folder in os.listdir(trials_dir):
                trial_folder_path = os.path.join(trials_dir, trial_folder)
                replay_data = os.listdir(trial_folder_path)
                play_data_paths = [os.path.join(trial_folder_path, rd) \
                    for rd in replay_data if 'play_game' in rd]
                feedback_data_paths = [os.path.join(trial_folder_path, rd) \
                    for rd in replay_data if 'give_feedback' in rd]

                participant = participants.get(trial_folder)
                if participant is None:
                    participant = Participant(
                        trial_folder,
                        experiment_id=experiment_id)
                
                if len(play_data_paths) > 0:
                    participant.play_data_paths = play_data_paths
                if len(feedback_data_paths) > 0:
                    participant.feedback_data_paths = feedback_data_paths

                participants[participant.uid] = participant

    return participants