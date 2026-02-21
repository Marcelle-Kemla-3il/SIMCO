import argparse
import os
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import gymnasium as gym
import matplotlib.pyplot as plt


# -----------------------
# Utils
# -----------------------
def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def moving_average(x, window=20):
    if len(x) < window:
        return float(np.mean(x)) if len(x) > 0 else 0.0
    return float(np.mean(x[-window:]))


# -----------------------
# Models (sans classes)
# -----------------------
def build_actor(obs_dim, n_actions, hidden=128):
    # sortie = probas d'actions
    return nn.Sequential(
        nn.Linear(obs_dim, hidden),
        nn.ReLU(),
        nn.Linear(hidden, hidden),
        nn.ReLU(),
        nn.Linear(hidden, n_actions),
        nn.Softmax(dim=-1),
    )


def build_critic(obs_dim, hidden=128):
    # sortie = V(s)
    return nn.Sequential(
        nn.Linear(obs_dim, hidden),
        nn.ReLU(),
        nn.Linear(hidden, hidden),
        nn.ReLU(),
        nn.Linear(hidden, 1),
    )


# -----------------------
# Train
# -----------------------
def train(args):
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    print("[INFO] Device:", device)

    env = gym.make("CartPole-v1")
    obs_dim = int(np.prod(env.observation_space.shape))
    n_actions = int(env.action_space.n)

    actor = build_actor(obs_dim, n_actions, hidden=args.hidden).to(device)
    critic = build_critic(obs_dim, hidden=args.hidden).to(device)

    opt_actor = optim.Adam(actor.parameters(), lr=args.lr_actor)
    opt_critic = optim.Adam(critic.parameters(), lr=args.lr_critic)

    rewards = []
    avg_rewards = []

    os.makedirs(args.out_dir, exist_ok=True)
    ckpt_path = os.path.join(args.out_dir, "actor_critic_cartpole.pt")

    for ep in range(1, args.episodes + 1):
        state, _ = env.reset(seed=args.seed + ep)
        done = False
        ep_return = 0.0
        steps = 0

        while not done and steps < args.max_steps:
            steps += 1

            s_t = torch.tensor(state, dtype=torch.float32, device=device)

            # Actor -> distribution
            action_probs = actor(s_t)
            dist = torch.distributions.Categorical(action_probs)
            action = dist.sample()

            next_state, reward, terminated, truncated, _ = env.step(action.item())
            done = bool(terminated or truncated)
            ep_return += float(reward)

            # Critic values
            v_s = critic(s_t).squeeze(0)  # V(s_t)

            with torch.no_grad():
                s2_t = torch.tensor(next_state, dtype=torch.float32, device=device)
                v_s2 = critic(s2_t).squeeze(0)  # V(s_{t+1})

            # TD error: δ = r + γ V(s') - V(s)
            r_t = torch.tensor(reward, dtype=torch.float32, device=device)
            delta = r_t + args.gamma * (0.0 if done else v_s2) - v_s

            # --- Critic update: MSE(delta) = delta^2
            loss_critic = delta.pow(2)

            opt_critic.zero_grad()
            loss_critic.backward()
            nn.utils.clip_grad_norm_(critic.parameters(), args.grad_clip)
            opt_critic.step()

            # --- Actor update: -log π(a|s) * delta
            log_prob = dist.log_prob(action)
            loss_actor = -(log_prob * delta.detach())

            opt_actor.zero_grad()
            loss_actor.backward()
            nn.utils.clip_grad_norm_(actor.parameters(), args.grad_clip)
            opt_actor.step()

            state = next_state

        rewards.append(ep_return)
        avg = moving_average(rewards, window=args.avg_window)
        avg_rewards.append(avg)

        if ep % args.log_every == 0 or ep == 1:
            print(f"Episode {ep:>4}/{args.episodes} | return={ep_return:>6.1f} | avg({args.avg_window})={avg:>6.1f}")

        # Sauvegarde si on progresse
        if ep >= args.avg_window and avg >= max(avg_rewards[:-1], default=-1e9):
            torch.save(
                {
                    "actor_state_dict": actor.state_dict(),
                    "critic_state_dict": critic.state_dict(),
                    "obs_dim": obs_dim,
                    "n_actions": n_actions,
                    "hidden": args.hidden,
                    "gamma": args.gamma,
                    "args": vars(args),
                },
                ckpt_path,
            )

        # Critère “TP” : moyenne >= 475
        if ep >= args.avg_window and avg >= 475.0:
            print(f"[SUCCESS] avg({args.avg_window}) >= 475 atteint à l'épisode {ep}.")
            break

    env.close()

    # Plot
    fig_path = os.path.join(args.out_dir, "reward_curve.png")
    plt.figure()
    plt.plot(rewards, label="Reward/episode")
    plt.plot(avg_rewards, label=f"Moving avg({args.avg_window})")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)

    print("[DONE] Training finished.")
    print("[CHECKPOINT]", ckpt_path)
    print("[PLOT]", fig_path)


# -----------------------
# Demo
# -----------------------
def demo(args):
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    ckpt = torch.load(args.model_path, map_location=device)

    obs_dim = int(ckpt["obs_dim"])
    n_actions = int(ckpt["n_actions"])
    hidden = int(ckpt.get("hidden", 128))

    actor = build_actor(obs_dim, n_actions, hidden=hidden).to(device)
    actor.load_state_dict(ckpt["actor_state_dict"])
    actor.eval()

    env = gym.make("CartPole-v1", render_mode="human")
    state, _ = env.reset(seed=args.seed)

    ep_return = 0.0
    for t in range(args.steps):
        s_t = torch.tensor(state, dtype=torch.float32, device=device)
        with torch.no_grad():
            probs = actor(s_t)
            action = int(torch.argmax(probs).item())  # greedy en démo

        state, reward, terminated, truncated, _ = env.step(action)
        ep_return += float(reward)

        if terminated or truncated:
            print(f"[DEMO] épisode terminé à t={t}, return={ep_return:.1f}")
            state, _ = env.reset()
            ep_return = 0.0

    env.close()


# -----------------------
# Main
# -----------------------
def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train")
    t.add_argument("--seed", type=int, default=42)
    t.add_argument("--cpu", action="store_true")

    t.add_argument("--episodes", type=int, default=1000)
    t.add_argument("--max_steps", type=int, default=500)

    t.add_argument("--gamma", type=float, default=0.99)
    t.add_argument("--lr_actor", type=float, default=1e-3)
    t.add_argument("--lr_critic", type=float, default=1e-3)
    t.add_argument("--hidden", type=int, default=128)
    t.add_argument("--grad_clip", type=float, default=5.0)

    t.add_argument("--avg_window", type=int, default=20)
    t.add_argument("--log_every", type=int, default=10)
    t.add_argument("--out_dir", type=str, default="runs_actor_critic_cartpole")

    d = sub.add_parser("demo")
    d.add_argument("--model_path", type=str, required=True)
    d.add_argument("--seed", type=int, default=123)
    d.add_argument("--steps", type=int, default=2000)
    d.add_argument("--cpu", action="store_true")

    args = p.parse_args()

    if args.cmd == "train":
        train(args)
    else:
        demo(args)


if __name__ == "__main__":
    main()
 