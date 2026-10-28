"use client";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Permission = "blog_create" | "blog_edit" | "blog_publish";
type User = { id: string; email: string; permissions: Permission[] };
const options: [Permission, string][] = [
  ["blog_create", "Create posts"],
  ["blog_edit", "Edit and submit posts"],
  ["blog_publish", "Publish approved posts"],
];
const base = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");
export default function BlogPermissions() {
  const [users, setUsers] = useState<User[]>([]);
  const [email, setEmail] = useState("");
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function request(method = "GET", body?: object) {
    const { data } = await createClient().auth.getSession();
    if (!data.session) throw new Error("Please sign in again.");
    const response = await fetch(`${base}/admin/blog-permissions`, {
      method,
      headers: {
        authorization: `Bearer ${data.session.access_token}`,
        "content-type": "application/json",
        "x-request-id": crypto.randomUUID(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(
        result.error?.message ??
          result.detail ??
          "Unable to update permissions.",
      );
    return result.data;
  }
  useEffect(() => {
    let active = true;
    request()
      .then((data: User[]) => {
        if (active) setUsers(data);
      })
      .catch((error: Error) => {
        if (active) setMessage(error.message);
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setMessage("");
          try {
            await request("PUT", { email, permissions });
            setUsers(await request());
            setMessage("Permissions saved.");
          } catch (error) {
            setMessage(
              error instanceof Error ? error.message : "Unable to save.",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          User email{" "}
          <input
            type="email"
            required
            maxLength={320}
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setPermissions([]);
            }}
          />
        </label>
        <fieldset disabled={busy}>
          <legend>Permissions</legend>
          {options.map(([permission, label]) => (
            <label
              key={permission}
              style={{ display: "block", padding: ".5rem" }}
            >
              <input
                type="checkbox"
                checked={permissions.includes(permission)}
                onChange={(event) =>
                  setPermissions(
                    event.target.checked
                      ? [...permissions, permission]
                      : permissions.filter((item) => item !== permission),
                  )
                }
              />{" "}
              {label}
            </label>
          ))}
        </fieldset>
        <button disabled={busy} type="submit">
          {busy ? "Saving…" : "Save permissions"}
        </button>
      </form>
      <p role="status" aria-live="polite">
        {message}
      </p>
      <h2>Users with blog permissions</h2>
      <ul>
        {users.map((user) => (
          <li key={user.id}>
            <button
              type="button"
              onClick={() => {
                setEmail(user.email);
                setPermissions(user.permissions);
              }}
            >
              {user.email}
            </button>
            :{" "}
            {user.permissions
              .map(
                (permission) =>
                  options.find(([key]) => key === permission)?.[1],
              )
              .join(", ")}
          </li>
        ))}
      </ul>
    </>
  );
}
