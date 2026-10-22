import { Layers2 } from "lucide-react";
import Link from "next/link";
export function Brand() {
  return (
    <Link href="/" className="brand">
      <span>
        <Layers2 size={20} />
      </span>
      recover<span className="brand-x">x</span>
      <sup>BETA</sup>
    </Link>
  );
}
