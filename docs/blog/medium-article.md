# My iPhone was still slow. So I asked my AI agent to investigate.

*A phone cleanup experiment that became an open-source skill for iPhone and Android.*

My iPhone was still slow after I had deleted a lot of stuff.

*I built this project. AI helped draft and edit this account of my phone-cleanup experiment.*

Typing felt sluggish. Scrolling did too. I had already tried the obvious cleanup, but I still didn't know what was causing it. So I asked my AI agent to review the phone and help me make some space.

The agent couldn't reach my iPhone directly from the chat. I opened iPhone Mirroring on my Mac and gave it a way to work through the phone's screens.

That was the start of the experiment. It also showed me how much an ordinary request leaves unsaid.

**“Clean up my phone” needs a few more instructions when the phone contains your passwords, sign-in codes and financial accounts.**

## The instructions I kept repeating

Keep the authenticators. Keep Duo. Keep the wallets and exchanges. Keep anything related to trading or finance. Ask me if you can't establish what an app is.

I also wanted a report before anything was removed. The agent could recommend what looked disposable. I wanted to see the list, change it and approve it once.

There was a useful detail in those cloud icons beside app names. On iPhone, offloading removes the app's software while keeping its documents and data. Deleting the remaining entry removes that saved data too. Downloading the app again may not bring the data back. [Apple explains how iPhone storage works.](https://support.apple.com/en-us/108429)

That matters for an old game. It matters much more for an authenticator or a wallet.

## I turned that conversation into a reusable skill

[Phone Health & Cleanup](https://github.com/shimoverse/iphone-health-cleanup) is a public, open-source project with separate iPhone and Android modules.

The idea is straightforward: put the recurring instructions into a workflow the assistant can reuse. Add local scripts for the repeated operations that the phone actually supports. Make the proposed changes visible before acting.

Once the relevant skill is installed and enabled in a compatible local assistant, you can ask:

> My phone is slow. Check its health and help me make some space.

You don't need to remember the skill's name. Selection still depends on the assistant and host; a GitHub link alone does not install it or grant phone access.

*A live recording of the agent operating iPhone Mirroring will be inserted here after capture and privacy review.*

## The report comes before the delete button

The assistant first collects the facts it can observe. That includes storage, available battery information and a question about what feels slow. A partial inventory needs to say that it is partial.

Then it presents three groups:

- **Recommend deleting:** ordinary apps and data proposed for removal, with reasons and consequences.
- **Keep:** protected apps and anything you explicitly want to retain.
- **Need your input:** uncertain identities, unclear recovery options or potentially important saved data.

You can override any recommendation. If a travel app is important for next week's trip, move it to Keep. Confidence does not take that decision away from you.

After you approve the exact list, the assistant starts with a small pilot and checks the result. The same unchanged list does not need another question before every tap. New targets need a new review.

The final report separates verified removals, failures and pending actions. It also checks that protected apps remain.

**Inspect → Review → Change the list → Approve → Small pilot → Verify**

## How it connects, and whether you can use your phone

For iPhone, there are two routes:

**iPhone Mirroring** provides supported screen-based review and cleanup on a compatible Mac and iPhone. The phone must stay nearby and locked. Using it directly interrupts Mirroring. The assistant needs reliable screen controls; if taps or scrolling stop working, it should stop uncertain actions and ask for help.

**Trusted USB** is the route for the included iPhone inventory and offloaded-app cleanup scripts. USB does not take over the screen. Ordinary phone use is generally possible during read-only checks. Keep it idle and connected during approved changes so the state does not change underneath the cleanup.

Android uses a separately authorized debugging connection, with a separate module and different safeguards. It is a preview too. Work profiles and secondary users are outside the current scripted cleanup scope.

## What it can do today

The iPhone scripts cover read-only baseline checks and approved removal of ordinary offloaded apps. Installed iPhone apps stay kept by default.

The Android module can inventory supported installed apps and handle approved removals. Cache-only cleanup is available only when the device advertises the required capability. It does not fall back to wiping app data.

Browser cleanup uses separately scoped native controls or guided steps. The project does not ship an automatic photo or video deletion engine. Favorites should remain protected.

The [README](https://github.com/shimoverse/iphone-health-cleanup#readme) explains installation, connection requirements and the limits for each route.

## What I am not claiming yet

I wanted this to be faster. Repeatedly navigating screens and checking apps is tedious, and supported scripts can reduce that repetition.

We have not measured the new scripted workflow's end-to-end time savings, token savings or storage recovery. Mirroring itself can be slow and unreliable. For a handful of apps, opening Settings yourself may be simpler.

Freeing storage also doesn't establish why a phone was slow. Battery wear, heat, connectivity, power settings and individual apps can matter. [Apple's performance guidance](https://support.apple.com/en-us/102598) and [Google's Pixel guidance](https://support.google.com/pixelphone/answer/6377329?hl=en) both cover causes beyond a full phone.

A useful test needs before-and-after free space, verified actions, total elapsed time and a repeat of the task that originally felt slow. Until that exists, a percentage speedup would be guesswork.

## A few questions I would ask before trying it

**Why not use Settings or a cleaner app?**

Use Settings when it solves the problem. This project is for people who already use a local assistant and want a reusable way to inspect, review and carry out supported changes. An iPhone cleaner app does not get broad access to other apps' private data just because it calls itself a cleaner.

**Can it delete something important?**

Yes, a mistake is still possible. The workflow keeps known sensitive apps, holds uncertain identities and requires approval of an exact list. The helpers check plans and device state along their supported path. None of that makes approved deletion reversible.

**What if the agent goes off-script?**

A skill is a set of instructions, not a complete security boundary. The helpers reject several unsafe requests, but an assistant with broader computer access may have other ways to act. Host permissions, a limited scope and reviewing the proposed list still matter.

**Does the skill copy my private data to GitHub?**

The helpers keep minimal reports locally. Phone inventories, connection records and logs belong outside the public repository. The assistant's model provider may receive text or screenshots it reads, depending on the host and its settings. Local helper scripts do not make every part of an AI session local.

**Is this a public ChatGPT plugin?**

The source is public on GitHub. A private personal ChatGPT plugin exists, but it is not a public directory release. A browser-only chat cannot operate a phone attached to your Mac just because the skill exists.

## Try a read-only check first

The project is a public preview. Its original code and documentation are MIT-licensed; [third-party dependency terms still apply](https://github.com/shimoverse/iphone-health-cleanup/blob/main/NOTICE.md). It builds on research into [iphone-app-manager](https://github.com/Nolikzero/claude-skills) and [pymobiledevice3's Device Operator](https://doronz88.github.io/pymobiledevice3/guides/codex-device-operator-skill/), with a separate Android approach.

Start with the [installation instructions](https://github.com/shimoverse/iphone-health-cleanup#install-ask-your-agent), ask for a read-only report and inspect the proposed list before approving changes.

I built this because I wanted help with an ordinary task and found myself explaining the boundaries as we went. Putting those boundaries into a skill gives the next run a clearer starting point. It gives me something concrete to review when I decide how much to trust an agent with data I care about.

*Disclosure: I built this project. AI assisted with implementation, research and editing; this article describes my own phone-cleanup experiment. The demo uses fictional apps. Scripted real-device performance remains unbenchmarked.*
