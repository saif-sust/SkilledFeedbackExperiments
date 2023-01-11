# HIPPO Gym
##### Human Input Parsing Platform for Openai Gym

Written by [Nick Nissen](https://nicknissen.com) and Yuan Wang
Supervised by [Matt Taylor](https://drmatttaylor.net) and Neda Navi
For the Intelligent Robot Learning Laboratory [(IRLL)](https://irll.ca) at the University of Alberta [(UofA)](https://ualberta.ca)
Supported by the Alberta Machine Intelligence Institure [(AMII)](https://amii.ca)

This is a modified version of the [original HIPPO Gym](https://github.com/IRLL/HIPPO_Gym) that has been adapted by [Edan Meyer](https://github.com/ejmejm) and [Saiful] (https://github.com/saif-sust).
This adapted version supports multiple advanced features like play vs. feedback trial types and different options for user input.

## Purpose:
HIPPO Gym is a framework for simplifying human-ai interaction research over the web.
The platform provides a communicator that opens a websocket to pass environment information to a browser-based front-end and recieve commands and actions from the front end. 

Built in Python, the framework is designed as a bring-your-own agent system where the framework provides an easy to impliment middle layer between a researcher's existing agent and a human interacting over the web. The framework is naive in that it makes no assumptions about how human input will be used, it simply provides the mechanism to pass along and record this information.

## Dependencies:

**System:** Linux, MacOs, WSL for Windows

**Packages:** Docker, AWS CLI

**Python** Python3.6+ required. Python3.7 recommended for Docker. Python3.8 used in AWS Lambda.

Note: At the time of writing OpenAI Gym supports up to Python3.7 

**PIP:** PyYaml, boto3, python-dotenv, gym, atari-py, shortuuid, asyncio, websockets, numpy, Pillow

Note: requirements.txt contains pip dependencies for building the Docker Image.

# Setup

1. Download AWS CLI https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html
    You will need to make two changes to make sure your account is authenticated:
    - Create a file with the path `~/.aws/credentials`, and format the contents as follows:
        ```
        [default]
        AWS_ACCESS_KEY_ID={ACCESS_KEY_HERE}
        AWS_SECRET_ACCESS_KEY={SECRET_KEY_HERE}
        ```
    - Create a file in this repo's `HGym-Feedback` folder called .env, and format the contents as follows:
        ```
        AWS_ACCESS_KEY_ID={ACCESS_KEY_HERE}
        AWS_SECRET_ACCESS_KEY={SECRET_KEY_HERE}
        ```

2. Download Docker: https://www.docker.com/pricing

3. Pull this repo. Cd into HGym-Feedback.

4. Install dependencies with `pip3 install -r requirements.txt`

# Testing

Below are instructions to make sure everything has been setup correctly, and will just use a sample config.
In the future when you eventually create your own experiment, you can repeat the below instructions to test it.

1. Cd into `HGym-Feedback`
2. Run `python3 updateProject.py -c configs/test_config.yml`
    - This will move around files and setup the project to run the experiment defined in the `test_config.yml` file.
    - Note that you will get a warning because no replay files have been setup yet; this is expected.
    - This will need to be rerun everytime you update the config file, or want to change the experiment you are testing.
3. Run the following to host the experiment locally:
    ```
    cd App/
    python3 communicator.py dev
    ```
4. Go to `https://irll.net/?server=ws://localhost:5000` in a browser to test the experiment.
    - After the first 3 episodes of the game, the program should throw an error due to no replay data being available.
    - You can now stop the program and move onto the next step.

Once you have local testing functional, you will want to confirm that docker testing also works:

1. Make sure Docker is running in the background (can be done by simply opening the app)
2. Open the `App/xvfb.sh` file and add the work "dev" at the end. The resulting contents should be:
    ```
    xvfb-run -s "-screen 0 1400x900x24" python3 communicator.py dev
    ```
    - This needs to be done whenever you want to test docker locally, but reverted later when you plan to upload your experiment to AWS.
3. Run the following commands from the `HGym-Feedback` directory to build and deploy the Docker container for your experiment:
    ```
    docker build -t hippo .
    docker run --publish 5000:5000 --rm --name hippo hippo
    ```
    - Note that the first command may take several minutes to build the container.
4. Just as done previously, you can now navigate to `https://irll.net/?server=ws://localhost:5000` in a browser to test your experiment.

Once you make a custom experiment, you will again want to follow these instructions for testing.
Running your project locally is much faster and should be done for all initial testing.
However, before publishing the experiment to AWS, you will always want to confirm that it works with Docker. There are sometimes Docker specific issues that appear, and they will need to be solved first if you want your experiment working on the AWS servers.

# Creating a Custom Experiment

Now that you have everything setup and working, you can start working on customizing the experiment you will want to run! In most cases this can be done entirely by just creating a new config file. The current repository handles all gym 2D environments, Atari environments, and a SuperMarioBros environment. If you want to add support for other environments that do not follow the standard gym conventions, you will need to modify the the `start()` function of the `Agent` class in the `agent.py` file.

*\*Note: if you are going to use an Atari environment, make sure to use the v5 version of it (e.g. ALE/MsPacman-v5). Full documentation for gym envs can be found at https://gymlibrary.ml/.*

## Config Setup

1. Copy and rename a config file from the `config/` folder. If you are going to be using an environment with a continuous actionspace, I would recommend using `lunar_lander_config.yml` as a base. If instad your environment has a discrete actionspace, I would recommend starting with `pacman_config.yml` as a base.
2. Change `useAWS` to `False` (we will change if back later before publishing the experiment).
3. Change the `id` and `name` fields to unique identifiers following the format in the base config.
4. Change the `researcher` field to your name, and the `teamMembers` field to everyone working on the project.
5. Next we will be modifying the `steps` field. Throughout the experiment, the participant will go through a mix of web forms (instructions, surveys, etc.) and game playing/feedback sessions. You will need to create the webpages using HTML (and optionally CSS in the same file, but no JavaScript), then add the pages to the `Steps/` folder. From there, list the pages in the order you want the participant to see them, making sure to number them in the format seen in the base config. For any step you want the participant to either play a game or give feedback, just write `game` for that step entry. Make sure that the steps start at index #1. Change the `finalStep` field to be the same as whatever the final step entry is.
6. Under the `events` field, change the `startServerStep` to 1, and `stopServerStep` to whatever the last step index is in your experiment.
7. Before when you changed the `steps` field, there was no differentiation between steps where the participant played the game and where they gave feedback to an agent. We can make that distinction with the `trial_types` field. For each time a `game` step appears in your config `steps`, you should have a corresponding entry in `trial_types`. A `play_game` entry specifies that the participant will play the game, whereas a `give_feedback` entry specifies that the participant will give feedback. The actual episodes to which they will give feedback will be addresses later.
8. Change `maxEpisodes` to be how many times you want the participant to play a game before moving onto a subsequent step. This only affects when the participant is playing a game and not when they are giving feedback.
9. Change the `game` field to gym name for the game you are using.
10. For specifying the actionspace and corresponding inputs to control the game, you need to define only one of 3 optional fields:

    a) `actionSpace` - The default actionspace specification provided by HippoGym. If you want to use this then you can follow the vanilla HippoGym instructions.

    b) `advancedActionSpace` - This allows for key combinations (e.g. right and up to move in a diagonal direction) and also better handles overlapping inputs. This is recommended if your environment has a discrete actionspace. Each entry should be a list with the combination of keys that need to be pressed to activate the corresponding action. When specifying the key bindings for each action, the order matters. For example, if in pacman, and actions of index 2 (indexed from 0) would move pacman upwards, then the 3rd entry under `advancedActionSpace` should be `['ArrowUp']`. An empty array (`[]`) can be used for no-ops. Make sure that there is an entry for each valid action in the environment.

    c) `continuousActionSpace` - This allows for continous action spaces and provides the other same benefits as the `advancedActionSpace`. This must be used if your actionspace is continuous. Each entry should be a list contianing 2 elements. The first should be a list of the combination of keys that need to be pressed to activate the corresponding action. The second element should be the action taken when the corresponding keys are pressed. For example, a lundar lander entry for a keybinding that goes up would be `[['ArrowUp'], [1, 0]]`. `['ArrowUp']` specified that the keybinding is just the up arrow, and `[1, 0]` specifies the action. For continuous lunar lander, an action of `[1, 0]` activates the thrusters to move the craft upwards. `[null, {REPLACE_WITH_DEFAULT_ACTION}]` and `[[], {REPLACE_WITH_DEFAULT_ACTION}]` should be added as defaults.

11. If you are using the `advancedActionSpace` or `continuousActionSpace`, you also need to add the `validKeys` field, which should be set to a list of all valid keys the participant can press when playing the game.
12. Change the `startingFrameRate` to the desired framerate. This is recommended to be whatever the game default is (usually 60) unless the game is too hard to play at that FPS (e.g. 20 FPS is much more manageable for something like lunar lander).
13. The `play_game_ui` and `give_feedback_ui` fields should be customized to have any buttons needed for you experiment. The only change I recommend making is setting `stop` to True in both UIs when testing so that you can easily skip through steps to quickly test your experiment.

If you want to edit any other fields, refer to the [HIPPO Gym website](https://hippogym.irll.net/guide/config.html) to read more.

At this point, you will want to test your experiment locally to make sure it works. At this point, everything except for the feedback trials should be functional.

## Feedback Setup

The next step is to record replay data that can be used for the feedback trials. During a feedback trial, the recorded epsiode(s) will be played back to the participant, who will be able to give positive or negative feedback at any point during the trial.

Below are instructions for recording and setting up feedback replay data:

1. Running your experiment locally, and play the game as many times as you need replays.
2. Navigate to the `App/Trials/` directory. Here you will see a file for each trial you completed in the format `play_game_trial_{trial_idx}_user_{uuid}`.
3. Rename eaech of these files to `replay_data_{idx}`. For example, the replay you want to be played for your first feedback trial should be named `replay_data_0`, and the one for the second trial should be `replay_data_1`.
3. Gzip each of the replay files. The resulting file names should be of the form `replay_data_{idx}.gz`.
4. Copy the gzipped data into the `App/AllReplayData/{experiment_name}` directory, replacing `{experiment_name}` with the `name` field in your config file. Create the directory if it does not already exist.
5. You can now rerun your experiment locally and test the feedback trials. You should be able to see your recorded episodes and give feedback without error.

## Publishing to AWS

After your experiment is fully functional, you will want to publish the experiment to AWS so that it can be played by participants.

1. Test your experiment with docker to make sure it works.
2. Change the config fields `useAWS` and `s3upload` to True.
3. Remove `dev` from the `App/xvfb.sh` file (though you will need to add it back for any future local testing with Docker).
3. Rerun the config update command: `python3 updateProject.py -c {CONFIG_PATH}`. The command will take some time, as it will build a Docker container for your experiment and upload it to AWS.
4. Once the above command is finished running, navigate to https://irll.net/?projectId={EXPERIMENT_ID} in a browser, replacing {EXPERIMENT_ID} with the `id` field in your config. Here, you can test the experiment to make sure it is fully functional.

# Getting Results

Once you or anyone else has completed the AWS hosted experiment, you will be able to download an analyze the data. At this point you will want to go back to the root repository directory and navigate to the `Analysis/` folder. Then follow these steps:

1. Open the `download_data.py` file and replace the `PROJECT_IDS` with the IDs of the experiments you are working with.
2. Run `python3 download_data.py` to download all the experiment data do the `data/` folder.
3. There is a file called `data_utils.py` that handles loading data for the predefined experiments in this repo. It should work fine for any other experiments for play and feedback data. However, it is hardcoded to work for the specific survey I use in these experiments, so that will need to be adjusted to work with any surveys or user data you collect.
4. Once you have made necessary changes, you can use the `load_participant_data()` function to return separate class instances with data for each participant. You can see an example of this working in the `EDA.ipynb` notebook.

# Other Tips

Here are some other useful tips:
- The repository comes with a `uuidScreen.html` file in the `Steps/` folder that can be used to give the user a unique ID. This should be used for MTurk where users need to enter a unique ID as proof they completed your experiment. When paying participants, you can check if the ID they entered matches one of the unique IDs from the participant data you downloaded.
- A `server.log` file should be generated under the `Apps/` directory that can help you debug any issues.

# More Info

More info about the specifics of certain files and other topics can be found on the [original HIPPO Gym repository](https://github.com/IRLL/HIPPO_Gym) and on the [HIPPO Gym website](https://hippogym.irll.net/).
