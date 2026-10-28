import Link from "next/link";
import {
  listPublishedPosts,
  type PublishedPostSummary,
} from "@/lib/editorial-content";
import styles from "./latest-blogs.module.css";

function imageUrl(value: string | null) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

export default async function LatestBlogs() {
  let posts: PublishedPostSummary[];
  try {
    posts = await listPublishedPosts({ language: "en", limit: 3 });
  } catch {
    // Keep the homepage useful when the separately deployed editorial API is unavailable.
    posts = [];
  }

  return (
    <section
      className={styles.section}
      id="latest-blogs"
      aria-labelledby="latest-blogs-title"
    >
      <div className={styles.heading}>
        <div>
          <h2 id="latest-blogs-title">Latest guides</h2>
          <p className={styles.intro}>
            The most recently published or re-verified guides.
          </p>
        </div>
        <Link className={styles.allLink} href="/blog">
          All guides
        </Link>
      </div>
      {posts.length ? (
        <div
          className={`${styles.grid} ${posts.length === 1 ? styles.single : ""}`}
        >
          {posts.map((post) => {
            const image = imageUrl(post.hero_image_url);
            const titleId = `latest-blog-${post.id}`;
            return (
              <article key={post.id} lang={post.language_code}>
                <Link
                  className={`${styles.card} ${image ? styles.hasImage : ""}`}
                  href={`/blog/${post.slug}`}
                  aria-labelledby={titleId}
                >
                  {image ? (
                    <div className={styles.media}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={image}
                        alt={post.hero_image_alt ?? post.title}
                        loading="lazy"
                        decoding="async"
                        width={1600}
                        height={1000}
                      />
                    </div>
                  ) : null}
                  <div className={styles.copy}>
                    <div className={styles.meta}>
                      <span>
                        {post.domain_slug?.replaceAll("-", " ") ?? "Uzbekistan"}
                      </span>
                      <time dateTime={post.published_at}>
                        {new Intl.DateTimeFormat(post.language_code, {
                          dateStyle: "medium",
                          timeZone: "UTC",
                        }).format(new Date(post.published_at))}
                      </time>
                    </div>
                    <h3 id={titleId}>{post.title}</h3>
                    <p className={styles.summary}>{post.summary}</p>
                    <span className={styles.readMore}>Read the guide</span>
                  </div>
                </Link>
              </article>
            );
          })}
        </div>
      ) : (
        <p className={styles.empty}>
          Published guides appear here. Browse all guides for travel ideas and
          practical information about Uzbekistan.
        </p>
      )}
    </section>
  );
}
