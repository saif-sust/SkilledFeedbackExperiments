'''
This is a demo file to be replaced by the researcher as required.
This file is imported by trial.py and trial.py will call:
start()
step()
render()
reset()
close()
These functions are mandatory. This file contains minimum working versions 
of these functions, adapt as required for individual research goals.
'''
import copy
import pickle
import gzip
import gym
from gym.wrappers import TimeLimit
from nes_py.wrappers import JoypadSpace
import gym_super_mario_bros
from gym_super_mario_bros.actions import COMPLEX_MOVEMENT

class Agent():
    '''
    Use this class as a convenient place to store agent state.
    '''

    def start(self, game:str, frameskip:int=1, max_frames:int=-1):
        '''
        Starts an OpenAI gym environment.
        Caller:
            - Trial.start()
        Inputs:
            -   game (Type: str corresponding to allowable gym environments)
        Returns:
            - env (Type: OpenAI gym Environment as returned by gym.make())
            Mandatory
        '''
        if 'ALE/' in game:
            self.env = gym.make(game, frameskip=frameskip, repeat_action_probability=0, full_action_space=False)
            self.render_obs = False
        elif 'SuperMarioBros-' in game:
            self.env = gym_super_mario_bros.make(game)
            self.env = JoypadSpace(self.env, COMPLEX_MOVEMENT)
            self.render_obs = False
        else:
            self.env = gym.make(game)
            self.render_obs = True

        if max_frames > 0:
            self.env = TimeLimit(self.env, max_episode_steps=max_frames)
        return self.env
    
    def step(self, action:int):
        '''
        Takes a game step.
        Caller: 
            - Trial.take_step()
        Inputs:
            - env (Type: OpenAI gym Environment)
            - action (Type: int corresponding to action in env.action_space)
        Returns:
            - envState (Type: dict containing all information to be recorded for future use)
              change contents of dict as desired, but return must be type dict.
        '''
        observation, reward, done, info = self.env.step(action)
        if self.render_obs:
            rgb_observation = self.env.render('rgb_array')
            envState = {
                'observation': rgb_observation, 'raw_observation': observation,
                'action': action, 'reward': reward, 'done': done, 'info': info}
        else:
            envState = {
                'observation': observation, 'reward': reward,
                'action': action, 'done': done, 'info': info}
        return envState
    
    def render(self):
        '''
        Gets render from gym.
        Caller:
            - Trial.get_render()
        Inputs:
            - env (Type: OpenAI gym Environment)
        Returns:
            - return from env.render('rgb_array') (Type: npArray)
              must return the unchanged rgb_array
        '''
        return self.env.render('rgb_array')
    
    def reset(self):
        '''
        Resets the environment to start new episode.
        Caller: 
            - Trial.reset()
        Inputs:
            - env (Type: OpenAI gym Environment)
        Returns: 
            No Return
        '''
        self.env.reset()
    
    def close(self):
        '''
        Closes the environment at the end of the trial.
        Caller:
            - Trial.close()
        Inputs:
            - env (Type: OpenAI gym Environment)
        Returns:
            No Return
        '''
        self.env.close()


def read_replay_buffer(path, trial_type):
    step_data = []
    with gzip.open(path, 'rb') as f:
        while f.peek(1):
            step_data.append(pickle.load(f))
    if trial_type == 'trial':
        step_data = step_data[0]
    return step_data

class ReplayAgent():
    '''
    Use this class as a convenient place to store agent state.
    '''

    def start(self, replay_path:str, data_file_type:str='episode'):
        '''
        Starts an OpenAI gym environment.
        Caller:
            - Trial.start()
        Inputs:
            -   game (Type: str corresponding to allowable gym environments)
        '''
        self.step_data = read_replay_buffer(replay_path, data_file_type)
        self.step_idx = 0
        self.curr_obs = self.step_data[self.step_idx]['observation']
    
    def step(self, action:int):
        '''
        Takes a game step.
        Caller: 
            - Trial.take_step()
        Inputs:
            - env (Type: OpenAI gym Environment)
            - action (Type: int corresponding to action in env.action_space)
        Returns:
            - envState (Type: dict containing all information to be recorded for future use)
              change contents of dict as desired, but return must be type dict.
        '''
        # observation, reward, done, info = self.env.step(action)
        # envState = {'observation': observation, 'reward': reward, 'done': done, 'info': info}
        self.step_idx += 1
        self.curr_obs = self.step_data[self.step_idx]['observation']
        return {'step': self.step_idx, 'done': self.step_data[self.step_idx]['done']}
    
    def render(self):
        '''
        Gets render from gym.
        Caller:
            - Trial.get_render()
        Inputs:
            - env (Type: OpenAI gym Environment)
        Returns:
            - return from env.render('rgb_array') (Type: npArray)
              must return the unchanged rgb_array
        '''
        return self.curr_obs
    
    def reset(self):
        '''
        Resets the environment to start new episode.
        Caller: 
            - Trial.reset()
        Inputs:
            - env (Type: OpenAI gym Environment)
        Returns: 
            No Return
        '''
        self.step_idx += 1
        self.curr_obs = self.step_data[self.step_idx]['observation']
        # self.env.reset()
    
    def close(self):
        '''
        Closes the environment at the end of the trial.
        Caller:
            - Trial.close()
        Inputs:
            - env (Type: OpenAI gym Environment)
        Returns:
            No Return
        '''
        # self.env.close()
        return
