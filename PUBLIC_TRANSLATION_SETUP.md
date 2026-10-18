# Public-content translation setup

External public-content translation is **off by default**. No provider or credentials are bundled. The supplied workflow also supports manual translation without an external service.

## Teacher workflow

1. Open the OWNER HTTPS website at `/teacher`, then **Public website translations**. Sign in with an administrator/teacher account. Student and guest accounts cannot access drafts or settings.
2. Choose the public field and target language. Studio introduction, teacher introduction and tagline come from the Teacher App’s website settings. Public announcements/lesson notes use announcement bodies. Only confirmed, scheduled public group descriptions are eligible; private lessons, instant meetings, messages, account records, filenames and student data are excluded. Public course descriptions have a separate original-description editor here. Titles and names are never automatically translated.
3. Add **all proper nouns** to Protected terms, one per line, especially single personal names and Chinese names. Public studio/teacher display names, math/code/URL spans, acronyms and capitalized multiword names are protected automatically. This is a conservative text filter, not a general proper-name recognition model: teachers must supply additional terms and review translations.
4. Enter a manual translation and **Save draft**, or configure a provider and explicitly enable external translation before generating a draft. Generate reuses an existing draft for the same original/language. Regenerate explicitly calls the provider again and may incur charges. Neither operation publishes a draft.
5. Review the preview in the textarea, edit it, then **Approve and publish translation**. Translations are plain text. HTML is shown literally, never executed. Math/URL/protected-term omissions are rejected. An approved translation stays published while a new draft is edited.
6. Students see an approved translation for their chosen EN/中文 language. Without one they see the original plus **Original (translation unavailable)**. A changed original immediately invalidates the previous translation by SHA-256; it must be translated and approved again. Drafts, approvals and configuration persist in the OWNER database, separately from originals. Concurrent stale edits return a conflict rather than overwriting another teacher’s draft.

## Provider-independent adapters

The plain-text adapter is `public_translations.translate(text, target, legacy)`. It receives only an allowlisted public description after protected spans have been replaced with opaque placeholders. Calls occur outside database transactions. A provider failure, altered placeholder, source edit, competing translation edit or teacher opt-out prevents publication. Credentials and upstream response bodies are not returned by the public/admin API. Authentication and CSRF remain enforced on every write.

### LibreTranslate over HTTPS (recommended configured adapter)

Configure these environment variables **on the OWNER process only**, through your existing private service/environment configuration:

| Variable | Value |
| --- | --- |
| `MATH_PUBLIC_TRANSLATION_PROVIDER` | `libretranslate` |
| `MATH_PUBLIC_TRANSLATION_URL` | Your trusted provider's full **HTTPS** `/translate` endpoint |
| `MATH_PUBLIC_TRANSLATION_API_KEY` | Your private provider key, if required |

Do not put the key in source, the URL, a ZIP, browser JavaScript or Teacher Ready. URLs containing embedded credentials, a query string or a fragment are rejected. Redirects are not followed, so a redirect cannot forward the key to another host. TLS verification remains enabled. The adapter sends POST JSON (`q`, `source:auto`, `target:en/zh`, `format:text`, optional `api_key`), with a 15-second timeout and bounded response size. Use a provider whose API supports these language codes and auto-detection. Restart the OWNER server after changing its environment, then explicitly opt in on the teacher translation page. No temporary tunnel URL or provider credentials are hardcoded.

On Windows, setting variables in a PowerShell process and starting `START STUDENT WEBSITE.bat` **from that same process** passes them to the OWNER. Store credentials using your normal protected service/environment configuration; do not edit a distributed launcher to contain a key. Unset the variables or select no provider to disable the adapter; uncheck the teacher opt-in to stop new generation immediately. No new Python dependency is required.

### Existing document translator (explicit optional reuse)

`MATH_PUBLIC_TRANSLATION_PROVIDER=legacy-google` explicitly reuses the existing `_translate_online` document-translation implementation. It uses an undocumented unauthenticated Google endpoint; no availability or support guarantee is implied. It is never selected automatically, and still requires the separate public-content teacher opt-in. Prefer a provider with documented service terms. Existing resource-code document translation remains separately controlled by each teacher-enabled share code and is unchanged.

## Verification and limits

No real provider was configured or called in this delivery. Automated tests use a synthetic adapter and simulated failures; browser checks use manually entered synthetic drafts. **Automatic provider operation has not been verified against a real service.** Before enabling a service, use authorized public test text with English and Chinese, LaTeX, names from Protected terms and URLs; inspect the returned draft, approve it deliberately, and verify the student's language view. Test rate limits, billing and outage behavior with your provider. A provider must preserve opaque placeholders exactly or its draft is rejected.

OS/browser-native permission prompts and validation bubbles follow the browser/OS language; application labels and diagnostics use the chosen website language. User-authored titles, course names, prices, messages, resource labels, filenames, formulas, URLs and identifiers intentionally retain their originals. They are not missing UI translations.
