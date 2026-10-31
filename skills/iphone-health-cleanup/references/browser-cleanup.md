# Browser cleanup via supported controls

This is a guided workflow, not a bundled browser-erasure API. Use an already available validated phone interface or give the user the specific steps. The executable app-removal runner must not be used to uninstall/reinstall browsers as a substitute.

History/cache can be covered by one explicit run authorization. Respect that scope without asking again per tap. Include timeframe, browser/profile and sync effects in the action table; cookies/site data can sign users out and remove offline website data. Do not infer permission for passwords, bookmarks, autofill, downloaded files, wallet data, tab closure or ongoing automatic-clear settings.

| Browser | Route to observe on the installed version | Scope safeguards |
|---|---|---|
| Safari | Settings > Apps > Safari > Clear History and Website Data; Advanced > Website Data for the history-preserving option | Full clearing combines history/site data. Check timeframe/profile and any tab-close option. Explain Safari/iCloud history effects before approval. |
| Chrome | More > Delete Browsing Data > Time Range / Browsing Data | Select only approved types. Autofill is separate; Google Account-saved history can be deleted across signed-in devices. Google My Activity is separate. |
| Brave | Menu > All Settings > Shields & Privacy > Clear Private Data | Avoid select-all. Preserve Saved Logins, Downloaded Files, wallet/site permissions and unrelated categories. Shred is a separate site action that closes its tabs; Auto Shred changes ongoing behavior. |
| Other browsers | Their actual in-app data controls | Check fields and version rather than assuming Safari's action clears another browser. |

Reopen the relevant view after execution and record observed results. Cache may regenerate, so zero remaining bytes is not a required universal success condition. Measure total phone free space separately; don't promise speed improvement from clearing cache.

Primary documentation: [Safari](https://support.apple.com/en-us/105082), [Chrome iPhone/iPad](https://support.google.com/chrome/answer/2392709?co=GENIE.Platform%3DiOS&hl=en), [Brave iOS privacy settings](https://support.brave.app/hc/en-us/articles/360053278131-How-do-I-manage-Shields-and-Privacy-settings-on-iOS), [Brave data-type descriptions](https://github.com/brave/brave-browser/issues/52550), [Brave Shred](https://support.brave.app/hc/en-us/articles/38161326430093-How-do-I-use-Shred-on-iOS).
