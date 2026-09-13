"use client";

import * as React from "react";
import { motion } from "motion/react";

/**
 * Shared entrance animation for page sections: a subtle fade + slide-up,
 * staggered by `delay`. Used on both the form page and the review page so
 * sections reveal in sequence rather than popping in all at once.
 */
export function PageSection({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
