"use client";

import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

export default function LoadingPulse({ text = "İşleniyor..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        className="mb-4 text-cobalt"
      >
        <Loader2 size={32} />
      </motion.div>
      <motion.p
        initial={{ opacity: 0.5 }}
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        className="text-sm font-medium tracking-wide text-mineral"
        style={{ letterSpacing: "0.1em" }}
      >
        {text}
      </motion.p>
      <div className="mt-6 h-1 w-48 overflow-hidden rounded-full bg-white/5">
        <motion.div
          className="h-full bg-gradient-to-r from-cobalt to-aqua"
          initial={{ x: "-100%" }}
          animate={{ x: "100%" }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    </div>
  );
}
