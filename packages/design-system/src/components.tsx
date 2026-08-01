import {
  forwardRef,
  useId,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";

type ButtonVariant = "primary" | "secondary" | "danger";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    { className = "", type = "button", variant = "primary", ...props },
    ref,
  ) {
    return (
      <button
        ref={ref}
        className={`uos-button uos-button--${variant} ${className}`.trim()}
        type={type}
        {...props}
      />
    );
  },
);

type FieldContentProps = {
  error?: string;
  hint?: string;
  id?: string;
  label: string;
};

function useFieldDescription({ error, hint, id }: FieldContentProps) {
  const generatedId = useId();
  const controlId = id ?? generatedId;
  const hintId = hint ? `${controlId}-hint` : undefined;
  const errorId = error ? `${controlId}-error` : undefined;
  return {
    controlId,
    describedBy: [hintId, errorId].filter(Boolean).join(" ") || undefined,
    errorId,
    hintId,
  };
}

function FieldMessages({
  error,
  errorId,
  hint,
  hintId,
}: FieldContentProps & {
  errorId?: string;
  hintId?: string;
}) {
  return (
    <>
      {hint ? (
        <p className="uos-field__hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="uos-field__error" id={errorId}>
          {error}
        </p>
      ) : null}
    </>
  );
}

export type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> &
  FieldContentProps;

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  function TextField(
    { className = "", error, hint, id, label, ...props },
    ref,
  ) {
    const description = useFieldDescription({ error, hint, id, label });
    return (
      <div className="uos-field">
        <label className="uos-field__label" htmlFor={description.controlId}>
          {label}
        </label>
        <input
          ref={ref}
          aria-describedby={description.describedBy}
          aria-invalid={error ? true : undefined}
          className={`uos-field__control ${className}`.trim()}
          id={description.controlId}
          {...props}
        />
        <FieldMessages
          {...description}
          error={error}
          hint={hint}
          label={label}
        />
      </div>
    );
  },
);

export type SelectFieldProps = Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  "id"
> &
  FieldContentProps;

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  function SelectField(
    { children, className = "", error, hint, id, label, ...props },
    ref,
  ) {
    const description = useFieldDescription({ error, hint, id, label });
    return (
      <div className="uos-field">
        <label className="uos-field__label" htmlFor={description.controlId}>
          {label}
        </label>
        <select
          ref={ref}
          aria-describedby={description.describedBy}
          aria-invalid={error ? true : undefined}
          className={`uos-field__control ${className}`.trim()}
          id={description.controlId}
          {...props}
        >
          {children}
        </select>
        <FieldMessages
          {...description}
          error={error}
          hint={hint}
          label={label}
        />
      </div>
    );
  },
);

export type CardProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
};

export function Card({ children, className = "", ...props }: CardProps) {
  return (
    <section className={`uos-card ${className}`.trim()} {...props}>
      {children}
    </section>
  );
}

type AlertTone = "info" | "success" | "warning" | "error";

export type AlertProps = HTMLAttributes<HTMLDivElement> & {
  message: string;
  title: string;
  tone?: AlertTone;
};

export function Alert({
  className = "",
  message,
  title,
  tone = "info",
  ...props
}: AlertProps) {
  const role = tone === "error" ? "alert" : "status";
  return (
    <div
      {...props}
      aria-live={tone === "error" ? "assertive" : "polite"}
      className={`uos-alert uos-alert--${tone} ${className}`.trim()}
      role={role}
    >
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}

type BadgeTone = "neutral" | "success" | "warning" | "danger";

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

export function Badge({
  className = "",
  tone = "neutral",
  ...props
}: BadgeProps) {
  return (
    <span
      className={`uos-badge uos-badge--${tone} ${className}`.trim()}
      {...props}
    />
  );
}

type StackGap = "sm" | "md" | "lg";

export type StackProps = HTMLAttributes<HTMLDivElement> & {
  gap?: StackGap;
};

export function Stack({ className = "", gap = "md", ...props }: StackProps) {
  return (
    <div
      className={`uos-stack uos-stack--${gap} ${className}`.trim()}
      {...props}
    />
  );
}
