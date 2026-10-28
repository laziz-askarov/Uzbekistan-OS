import styles from "./seed-cluster.module.css";

/** The logo's 2x2 seed cluster in the current section colour: marks a callout. */
export function SeedCluster() {
  return (
    <span className={styles.seed} aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}
