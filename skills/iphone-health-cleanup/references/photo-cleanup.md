# On-phone photo cleanup: proposed extension

**Design only. No photo scanner or photo-deletion executor is included in this release.** Do not present the app inventory or a USB media listing as a real blur assessment. Mac Photos-library setup is outside the intended flow.

The goal is a short, useful report of likely failed images and large videos, followed by a bounded approved cleanup. Use Apple's existing organization and duplicate review where available; custom album creation is not required.

## Needed access

An authorized on-phone scanner/native helper or an already available suitable app must supply asset identities, fresh Favorites state, quality evidence and actual file/resource availability. A skill document or Mirroring window cannot grant PhotoKit access. Never claim that all photos were scanned if access is limited or originals are unavailable.

[TidyByte](https://github.com/360ghar/tidybyte) offers open-source on-device blur/similarity/large-file code to evaluate. Its reviewed bulk deletion paths do not meet an absolute Favorites prohibition unchanged. [CleanMyPhone](https://macpaw.com/support/cleanmyphone/faq) is a commercial on-phone example of categorized review; an agent automation interface has not been verified. These are research leads, not bundled integrations.

## Proposed rules

- Never delete, unfavorite or retire a Favorite through merging. Missing/uncertain Favorite status means skip. Check again at execution time, not only during planning.
- High confidence that a photo is blurry does not establish that it is disposable. Clear accidental failures with a sharper retained equivalent are stronger candidates; unique memories and readable documents remain for review.
- Preserve receipts, personal documents, Hidden/shared items and complex resource bundles unless a separate, supported scope handles them correctly.
- Examine video duration, audio and multiple frames. File size, a black opening frame or a blurry poster frame alone is not deletion evidence. Compression is a separate decision.
- Compare complete resources for exact copies. Matching a thumbnail or a Live Photo's still does not prove the motion component is identical.

## Proposed report and action

For each group show thumbnails, reason, confidence explanation, count, estimated bytes, protected/excluded items and a retained survivor where applicable. One approval can cover a stable batch; it need not create a prompt for each photo. The controller must still use the platform's supported confirmation and verify protected assets/survivors afterward.

Keep an action manifest locally and measure actual iPhone free-space change separately from original-library byte estimates. Cloud optimization can make those figures differ. Do not empty Recently Deleted automatically or promise universal recovery; synced deletion, Shared Albums, Recovered items and quota conditions can have different consequences. [Apple deletion guidance](https://support.apple.com/en-lamr/104967), [iCloud storage guidance](https://support.apple.com/en-gb/108922).
