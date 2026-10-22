import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

const getCurrentUserMock = vi.fn();
vi.mock("@/lib/auth", () => ({
  getCurrentUser: () => getCurrentUserMock(),
  logout: vi.fn(),
}));

import Sidebar from "./Sidebar";

describe("Sidebar", () => {
  it("renders every primary navigation route", () => {
    getCurrentUserMock.mockReturnValue(new Promise(() => {})); // never resolves
    render(<Sidebar />);

    for (const label of ["Genel Bakış", "Profil", "CV Analizi", "Başvurular"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("shows the user's full name once loaded, instead of the generic placeholder", async () => {
    getCurrentUserMock.mockResolvedValue({
      id: 1,
      email: "ayse@example.com",
      full_name: "Ayşe Yılmaz",
      is_active: true,
    });
    render(<Sidebar />);

    expect(await screen.findByText("Ayşe Yılmaz")).toBeInTheDocument();
    expect(screen.queryByText("Kariyer Adayı")).not.toBeInTheDocument();
  });

  it("falls back to the generic placeholder when /auth/me fails", async () => {
    getCurrentUserMock.mockRejectedValue(new Error("network error"));
    render(<Sidebar />);

    await waitFor(() => expect(getCurrentUserMock).toHaveBeenCalled());
    expect(await screen.findByText("Kariyer Adayı")).toBeInTheDocument();
  });
});
