import gym
import tensorflow as tf
import numpy as np
from collections import deque
from time import time
from sklearn.grid_search import ParameterGrid
from replay_memory import ReplayMemory
from dqn import DQN

SOLVED_MEAN_REWARD = 195.0
MAX_STEPS = 200
MAX_EPISODES = 200
MAX_HISTORY = 100
MODEL_PATH = 'models/dqn.tfl'

param_sets = {
    'gamma': [0.99, 0.95, 0.90],
    'learning_rate': [1., 0.1],
    'e_anneal_steps': [1000, 10000],
    'n_epoch': [1, 2]
}
param_grid = list(ParameterGrid(param_sets))
print(len(param_grid))
print(param_grid)
# {'learning_rate': 1.0,
#  'n_epoch': 1,
#  'gamma': 0.99,
#  'e_anneal_steps': 1000}
# param = {
#     'gamma': 0,
#     'learning_rate': 0,
#     'e_anneal_steps': 0,
#     'n_epoch': 0
# }
# will make a matrix that enumerates these params
# find numpy method


# also each param that runs over history, needs also be averaged over
# many runs (the instability effects)

# Hyper param outline:
# make multiple envs, init new mem, try a dqn param
# optimize for scores
# dqn params:
# gamma, learning_rate, e_anneal_steps, n_epoch? net param
# feed as dict, spread as named param into DQN()
# do parallel matrix select

# output metrics:
# - if solved, solved_in_epi = (epi-MAX_HISTORY). use solved_avg/solved_in_epi
# - else unsolved, avg (all must hit MAX_EPISODES). use avg/MAX_EPISODES

# solved_avg > avg
# solved_in_epi < MAX_EPISODES
# ok so ordering is ensured
#
# use avg/epi is sufficient for each hisotry of a param
# do multiple history runs of the same param, take average of that val
# pick the max param

# also need to see if it's already solved
# also need an early-giveup mechanism

# borrow SkFlow/scikit to enum param dict matrix
# for each param (parallelize):
#   for H times:
#       run_session(param), return metric, append list
#       update average of metric, terminate if avg too shitty
#    return its avg_metric
#  select the param that yields the max avg metric


def get_env_spec(env):
    '''
    Helper: return the env specs: dims, actions
    '''
    return {
        'state_dim': env.observation_space.shape[0],
        'state_bounds': np.transpose(
            [env.observation_space.low, env.observation_space.high]),
        'action_dim': env.action_space.n,
        'actions': list(range(env.action_space.n))
    }


def update_history(epi_history, total_rewards, epi, total_t, epi_time):
    '''
    Helper: update the hisory, max len = MAX_HISTORY
    report status
    return [bool] solved
    '''
    epi_history.append(total_rewards)
    mean_rewards = np.mean(epi_history)
    avg_speed = float(epi_time)/float(total_t)
    logs = [
        '{:->20}'.format(''),
        'Episode {}'.format(epi),
        'Finished at t={}, reward={}'.format(total_t, total_rewards),
        'Average reward for the last {} episodes: {:.4f}'.format(
            MAX_HISTORY, mean_rewards),
        'Average time per step {:.4f} s/step'.format(avg_speed)
    ]
    solved = mean_rewards >= SOLVED_MEAN_REWARD
    early_exit = bool(
        epi > float(MAX_EPISODES)/2. and mean_rewards < SOLVED_MEAN_REWARD/2.)
    print('\n'.join(logs))
    if solved or (epi == MAX_EPISODES - 1):
        print('Problem solved? {}'.format(solved))
    return mean_rewards, solved, early_exit


def run_episode(epi_history, env, replay_memory, dqn, epi):
    '''
    run an episode
    return [bool] if the problem is solved by this episode
    '''
    total_rewards = 0
    start_time = time()
    state = env.reset()
    replay_memory.reset_state(state)

    for t in range(MAX_STEPS):
        # env.render()
        action = dqn.select_action(state)
        next_state, reward, done, info = env.step(action)
        replay_memory.add_exp(action, reward, next_state, done)
        dqn.train(replay_memory)
        state = next_state
        total_rewards += reward
        if done:
            break

    epi_time = time() - start_time
    return update_history(epi_history, total_rewards, epi, t, epi_time)


def run_session(param={}):
    '''
    primary method
    '''
    epi_history = deque(maxlen=MAX_HISTORY)
    env = gym.make('CartPole-v0')
    env_spec = get_env_spec(env)
    sess = tf.Session()
    replay_memory = ReplayMemory(env_spec)
    dqn = DQN(env_spec, sess, **param)

    # dqn.restore(MODEL_PATH+'-30')
    for epi in range(MAX_EPISODES):
        mean_rewards, solved, early_exit = run_episode(
            epi_history, env, replay_memory, dqn, epi)
        if solved or early_exit:
            break

    # dqn.save(MODEL_PATH)  # save final model
    param_score = mean_rewards/float(epi)
    return solved, param_score


# if __name__ == '__main__':
#     run_session()