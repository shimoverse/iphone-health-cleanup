My iPhone was still slow, even after I'd deleted a lot of stuff.

So I asked my AI agent to review the phone and help figure out what else might be going on.

It couldn't access the iPhone directly from the chat. I opened iPhone Mirroring on my Mac so we had a way to work through the phone's interface.

As we went, I kept adding instructions: keep the authenticators, wallets, exchanges and password managers. Check app identities. Ask me when unsure. Don't treat “make space” as permission to delete anything.

I wanted a way to carry that understanding into the next conversation. That led to Phone Health & Cleanup, a reusable skill with an exact review list, approval before changes, a small pilot and checks on the result.

It now has separate iPhone and Android modules, with local scripts for supported operations and guided screen steps for other tasks.

The skill does not make the agent fully predictable. The helpers enforce checks on their own path, but an agent with broader host access could bypass them. Human review and permissions still matter.

We have 98 passing offline tests. Real-device compatibility and any time, storage or performance benefits of the new workflow remain unverified.

This is a small daily-life experiment: make the instructions clearer, make decisions visible, and check what happened. That gives me a better basis for deciding how much to delegate to an agent.

Source, guardrails and setup: https://github.com/shimoverse/iphone-health-cleanup
