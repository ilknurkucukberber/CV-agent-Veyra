import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";

const apiFetchMock = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  getToken: () => "test-token",
}));

import ResumeGate from "./ResumeGate";

describe("ResumeGate", () => {
  beforeEach(() => {
    localStorage.clear();
    apiFetchMock.mockReset();
  });

  it("prompts for an upload when there is no active resume", async () => {
    apiFetchMock.mockResolvedValue([]);
    render(<ResumeGate>{(id) => <div>CV #{id} hazır</div>}</ResumeGate>);

    expect(await screen.findByText("CV’ni sisteme tanıt.")).toBeInTheDocument();
    expect(screen.queryByText(/hazır$/)).not.toBeInTheDocument();
  });

  it("surfaces previously uploaded resumes so the user isn't forced to re-upload", async () => {
    apiFetchMock.mockResolvedValue([
      {
        id: 42,
        title: "eski_cv",
        original_filename: "eski_cv.pdf",
        parse_status: "completed",
        is_primary: true,
        created_at: new Date().toISOString(),
      },
    ]);
    render(<ResumeGate>{(id) => <div>CV #{id} hazır</div>}</ResumeGate>);

    expect(await screen.findByText("eski_cv")).toBeInTheDocument();
    expect(screen.getByText("Birincil")).toBeInTheDocument();
  });

  it("reprocesses a failed resume without uploading or discarding it", async () => {
    localStorage.setItem("active_resume_id", "42");
    let retried = false;
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.endsWith("/retry-parse")) {
        retried = true;
        return { id: 42 };
      }
      return { id: 42, parse_status: retried ? "completed" : "failed", parse_error: "Servis hatası" };
    });
    render(<ResumeGate>{(id) => <div>CV #{id} hazır</div>}</ResumeGate>);
    await userEvent.click(await screen.findByRole("button", { name: "Yeniden işle" }));
    expect(await screen.findByText("CV #42 hazır")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith("/resumes/42/retry-parse", { method: "POST" });
    expect(localStorage.getItem("active_resume_id")).toBe("42");
  });
});
