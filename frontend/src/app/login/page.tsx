"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import axios from "axios";
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useRouter } from "next/navigation";

import {
  getCurrentUser,
  login,
} from "@/lib/auth-api";
import {
  getAccessToken,
  setAccessToken,
  setStoredUser,
} from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();

  const [
    username,
    setUsername,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    showPassword,
    setShowPassword,
  ] = useState(false);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  useEffect(() => {
    if (getAccessToken()) {
      router.replace("/dashboard");
    }
  }, [router]);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const token = await login(
        username.trim(),
        password,
      );

      setAccessToken(
        token.access_token,
      );

      const user =
        await getCurrentUser();

      setStoredUser(user);

      router.replace("/dashboard");
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        const detail =
          requestError.response?.data?.detail;

        setError(
          typeof detail === "string"
            ? detail
            : (
              "Unable to sign in. "
              + "Please check your credentials."
            ),
        );
      } else {
        setError(
          "Unable to connect to the server.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-brand-panel">
        <div className="brand-badge">
          <img
            src="/bandara-cool-world-logo.png"
            alt="Bandara Cool World logo"
            className="login-brand-logo"
          />
          BANDARA COOL WORLD
        </div>

        <div className="brand-copy">
          <p className="eyebrow">
            OPERATIONS PLATFORM
          </p>

          <h1>
            One system for your
            entire cooling business.
          </h1>

          <p>
            Manage sales, customers,
            inventory, payments, returns,
            service jobs and financial
            operations from one secure
            workspace.
          </p>
        </div>

        <div className="security-note">
          <ShieldCheck size={22} />

          <div>
            <strong>
              Secure internal access
            </strong>

            <span>
              Protected by role-based
              permissions and authenticated
              sessions.
            </span>
          </div>
        </div>
      </section>

      <section className="login-form-panel">
        <div className="login-card">
          <div className="mobile-logo">
            <img
              src="/bandara-cool-world-logo.png"
              alt="Bandara Cool World logo"
              className="login-brand-logo"
            />
            BANDARA COOL WORLD
          </div>

          <div className="login-heading">
            <p className="eyebrow">
              WELCOME BACK
            </p>

            <h2>
              Sign in to continue
            </h2>

            <p>
              Enter your authorized
              account credentials.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="login-form"
          >
            <label>
              Username or email

              <div className="input-shell">
                <UserRound size={19} />

                <input
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(event) =>
                    setUsername(
                      event.target.value,
                    )
                  }
                  placeholder="Enter username"
                  required
                />
              </div>
            </label>

            <label>
              Password

              <div className="input-shell">
                <LockKeyhole size={19} />

                <input
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.target.value,
                    )
                  }
                  placeholder="Enter password"
                  required
                />

                <button
                  type="button"
                  className="icon-button"
                  aria-label={
                    showPassword
                      ? "Hide password"
                      : "Show password"
                  }
                  onClick={() =>
                    setShowPassword(
                      (value) => !value,
                    )
                  }
                >
                  {showPassword
                    ? <EyeOff size={18} />
                    : <Eye size={18} />
                  }
                </button>
              </div>
            </label>

            {error && (
              <div className="form-error">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="primary-button"
              disabled={loading}
            >
              <span>
                {loading
                  ? "Signing in..."
                  : "Sign in"
                }
              </span>

              {!loading && (
                <ArrowRight size={19} />
              )}
            </button>
          </form>

          <p className="login-footer">
            Bandara Cool World Management System
            <span>•</span>
            Authorized personnel only
          </p>
        </div>
      </section>
    </main>
  );
}
