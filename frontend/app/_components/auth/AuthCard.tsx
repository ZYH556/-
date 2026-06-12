"use client";

import { FormEvent } from "react";
import Image from "next/image";

export type AuthMode = "login" | "register";
type LoginStatus = "checking" | "idle" | "submitting" | "error";

interface AuthCardProps {
  mode: AuthMode;
  status: LoginStatus;
  username: string;
  password: string;
  registerAccount: string;
  confirmPassword: string;
  error: string;
  onModeChange: (mode: AuthMode) => void;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onRegisterAccountChange: (value: string) => void;
  onConfirmPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSocial: (provider: "google" | "github") => void;
}

export function AuthCard({
  mode,
  status,
  username,
  password,
  registerAccount,
  confirmPassword,
  error,
  onModeChange,
  onUsernameChange,
  onPasswordChange,
  onRegisterAccountChange,
  onConfirmPasswordChange,
  onSubmit,
  onSocial,
}: AuthCardProps) {
  const checked = mode === "register";

  return (
    <section className="doodle-wrapper">
      <input
        type="checkbox"
        id="doodle-flip"
        className="doodle-toggle"
        aria-label="Toggle Login and Sign up"
        checked={checked}
        onChange={(event) => onModeChange(event.target.checked ? "register" : "login")}
      />

      <div className="doodle-header">
        <span className="doodle-mode-text login-text">Log in</span>
        <label className="doodle-switch-label" htmlFor="doodle-flip" tabIndex={0}>
          <span className="doodle-switch-handle" />
        </label>
        <span className="doodle-mode-text signup-text">Sign up</span>
      </div>

      <div className="doodle-card-scene">
        <DoodleDecorations />
        <div className="doodle-card-inner">
          <div className="doodle-card-front">
            <div className="doodle-title">Welcome!</div>
            <form className="doodle-form" onSubmit={onSubmit}>
              <div className="doodle-input-wrapper">
                <input
                  className="doodle-input"
                  name="username"
                  placeholder="Account"
                  type="text"
                  value={username}
                  onChange={(event) => onUsernameChange(event.target.value)}
                  autoComplete="username"
                  required
                />
              </div>
              <div className="doodle-input-wrapper">
                <input
                  className="doodle-input"
                  name="password"
                  placeholder="Password"
                  type="password"
                  value={password}
                  onChange={(event) => onPasswordChange(event.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>
              <button className="doodle-btn" disabled={status === "submitting"}>
                {status === "submitting" ? "Wait..." : "Let's Go!"}
              </button>
            </form>
            <SocialButtons status={status} onSocial={onSocial} />
          </div>

          <div className="doodle-card-back">
            <div className="doodle-title doodle-title-alt">Join Us!</div>
            <form className="doodle-form" onSubmit={onSubmit}>
              <div className="doodle-input-wrapper">
                <input
                  className="doodle-input"
                  name="account"
                  placeholder="Phone or Email"
                  type="text"
                  value={registerAccount}
                  onChange={(event) => onRegisterAccountChange(event.target.value)}
                  autoComplete="email"
                  required
                />
              </div>
              <div className="doodle-input-wrapper">
                <input
                  className="doodle-input"
                  name="password"
                  placeholder="Password"
                  type="password"
                  value={password}
                  onChange={(event) => onPasswordChange(event.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
              <div className="doodle-input-wrapper">
                <input
                  className="doodle-input"
                  name="confirmPassword"
                  placeholder="Confirm"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => onConfirmPasswordChange(event.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
              <button className="doodle-btn doodle-btn-alt" disabled={status === "submitting"}>
                {status === "submitting" ? "Wait..." : "Confirm!"}
              </button>
            </form>
            <SocialButtons status={status} onSocial={onSocial} />
          </div>
        </div>
      </div>

      {status === "error" && <div className="doodle-error">{error}</div>}
    </section>
  );
}

function DoodleDecorations() {
  return (
    <>
      <svg
        className="doodle-svg doodle-star"
        viewBox="0 0 24 24"
        fill="#ffd166"
        stroke="var(--ink)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
      <svg
        className="doodle-svg doodle-sparkle"
        viewBox="0 0 24 24"
        fill="#06d6a0"
        stroke="var(--ink)"
        strokeWidth="1.5"
      >
        <path d="M12 2 Q12 12 22 12 Q12 12 12 22 Q12 12 2 12 Q12 12 12 2 Z" />
      </svg>
      <svg
        className="doodle-svg doodle-swirl"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--ink)"
        strokeWidth="1.5"
        strokeLinecap="round"
      >
        <path d="M3 12 C 3 5 10 5 16 5 C 20 5 21 9 18 12 C 15 15 10 13 12 9 C 14 5 22 9 21 16" />
      </svg>
    </>
  );
}

function SocialButtons({
  status,
  onSocial,
}: {
  status: LoginStatus;
  onSocial: (provider: "google" | "github") => void;
}) {
  return (
    <div className="doodle-social-row">
      <SocialButton
        icon="/google.svg"
        label="Google"
        status={status}
        onClick={() => onSocial("google")}
      />
      <SocialButton
        icon="/github_dark.svg"
        label="GitHub"
        status={status}
        onClick={() => onSocial("github")}
        darkIcon
      />
    </div>
  );
}

function SocialButton({
  icon,
  label,
  status,
  onClick,
  darkIcon = false,
}: {
  icon: string;
  label: string;
  status: LoginStatus;
  onClick: () => void;
  darkIcon?: boolean;
}) {
  return (
    <button
      type="button"
      className="doodle-social-btn"
      onClick={onClick}
      disabled={status === "submitting"}
    >
      <span className={darkIcon ? "doodle-social-icon-dark" : ""}>
        <Image src={icon} alt="" width={darkIcon ? 13 : 16} height={darkIcon ? 13 : 16} />
      </span>
      {label}
    </button>
  );
}
