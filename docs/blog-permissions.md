# Blog permissions

The public blog at `/blog` uses the existing versioned editorial publication workflow. Staff work at `/admin/content`. Administrators manage grants at `/admin/blog-permissions`, also linked from the account page and blog studio.

Apply the API migration before deploying the updated web/API applications:

```sh
cd apps/api
python -m alembic upgrade head
```

Revision `20261027_0013` adds three independent roles:

- `blog_create`: create author profiles and new posts.
- `blog_edit`: edit drafts, create revisions, and submit drafts for review.
- `blog_publish`: publish approved revisions.

Grant both create and edit for a writer who will maintain and submit their own posts. Editing applies to all editorial drafts in the shared studio. Publishing does not grant review/approval access. Existing `content_author`, `content_reviewer`, `knowledge_publisher`, and `admin` roles keep their existing privileges.

An administrator enters the email of an existing, non-anonymous Supabase account and selects permissions. Saving replaces only these three grants; clearing all boxes revokes them. The API provisions the internal principal on first grant. It resolves the email against `auth.users`, so the API database connection needs read access to that table as well as its existing identity/audit access. No client database grants or access-token hook changes are needed.

Every grant change and its before/after permission set is recorded atomically in the API audit log with actor and request ID. API authorization reads current database assignments on every request, so revocation does not depend on token refresh. A loaded studio may display old controls until refreshed, but subsequent API requests enforce the current grants.

Drafts remain private. Only approved revisions can be published, with the existing citation and source eligibility checks. Blogs are excluded from assistant retrieval unless explicitly opted in and eligible under the existing editorial rules.

Validation: run the repository web/API suites and `python scripts/validate_contracts.py`. Database integration tests require disposable infrastructure; deployment migrations must be applied separately.

## Images, publishing, and discovery

Administrators can use **Save & publish now** to save, submit, approve, and publish through the same API state/evidence checks in one action. Other staff keep the reviewed workflow. Publication goes through a session-authenticated server route that expires the public editorial cache only after API publication succeeds.

Writers can upload JPEG, PNG, and WebP images up to 3 MB and 20 megapixels. The image route asks the API to authorize the current principal, decodes the bytes, applies orientation, strips metadata, resizes to at most 2400×2400, and stores WebP in the public `blog-images` bucket. Only the server storage client writes objects. Image descriptions are required by the upload UI; body images use Markdown and render without raw HTML. Cover images display on the article page and participate in its metadata.

The production image bucket was provisioned with public reads, a 3 MB object limit, and `image/webp` as its allowed MIME type. New environments must provision that bucket with the same settings before uploads are enabled; do not grant browser write policies.

The studio provides title/description preview, key takeaways, and FAQ fields. Published content continues to expose server-rendered HTML, matching BlogPosting/FAQ structured data, canonical and language links, author/dates/sources, RSS, sitemap entries, and Markdown editions. Public search crawlers retain access while private application routes remain disallowed. None of these controls promises indexing or ranking.

Official guidance consulted:

- [OpenAI search crawler](https://developers.openai.com/api/docs/bots)
- [Anthropic crawler controls](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)
- [Google AI search features](https://developers.google.com/search/docs/appearance/ai-features)

Google does not require special AI markup or llms.txt for its AI search features; these supplementary text feeds do not guarantee inclusion in Google, Gemini, ChatGPT, or Claude.
