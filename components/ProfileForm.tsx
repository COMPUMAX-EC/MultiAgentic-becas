"use client";

import { ChangeEvent, FormEvent, useCallback, useRef, useState } from "react";
import { ProcessingState } from "./ProcessingState";
import { ScholarshipResults } from "./ScholarshipResults";
import { mockScholarships } from "../src/data/mockScholarships";
import { ScholarshipResult } from "../types/scholarship";

export function ProfileForm() {
  const preparedSubmissionRef = useRef<FormData | null>(null);
  const [profileText, setProfileText] = useState("");
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [profileError, setProfileError] = useState("");
  const [processingRunId, setProcessingRunId] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [scholarshipResults, setScholarshipResults] =
    useState<ScholarshipResult[]>(mockScholarships);

  const handleProcessingComplete = useCallback(() => {
    setIsProcessing(false);
    setShowResults(true);
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedProfile = profileText.trim();

    if (!trimmedProfile) {
      setProfileError("Describe your profile and scholarship goals before submitting.");
      return;
    }

    if (fileError) {
      return;
    }

    preparedSubmissionRef.current = buildSubmissionFormData(trimmedProfile, cvFile);
    setProfileError("");
    setHasSubmitted(true);
    setShowResults(false);
    setScholarshipResults(mockScholarships);
    setIsProcessing(true);
    setProcessingRunId((currentRunId) => currentRunId + 1);
  }

  function handlePdfChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0] || null;

    if (!selectedFile) {
      setCvFile(null);
      setFileError("");
      return;
    }

    const isPdf =
      selectedFile.type === "application/pdf" ||
      selectedFile.name.toLowerCase().endsWith(".pdf");

    if (!isPdf) {
      event.target.value = "";
      setCvFile(null);
      setFileError("Only PDF files are accepted for the CV/resume upload.");
      return;
    }

    setCvFile(selectedFile);
    setFileError("");
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="input-panel">
        <p className="section-kicker">Profile input</p>
        <h2>Ingresa tu perfil y el tipo de beca al que tú quieres aplicar</h2>
        <p className="input-helper">
          Include your academic profile, nationality, languages, study area,
          target countries, and scholarship goals in one place.
        </p>

        <label className="field-group profile-textarea">
          <span>Your profile and scholarship goals</span>
          <textarea
            value={profileText}
            onChange={(event) => {
              setProfileText(event.target.value);
              setProfileError("");
            }}
            placeholder="Soy estudiante colombiano de ingeniería de sistemas, hablo español e inglés B2, quiero aplicar a becas de maestría en Canadá o Alemania para inteligencia artificial..."
          />
          <small>
            A natural paragraph is perfect. Structured extraction can be wired
            to the backend later without changing this form.
          </small>
        </label>

        <label className="field-group file-field">
          <span>CV/resume PDF (optional)</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={handlePdfChange}
          />
          <small>
            {cvFile
              ? `Selected file: ${cvFile.name}`
              : "PDF only. The file is kept ready for a future multipart/form-data submission."}
          </small>
        </label>

        {profileError ? <p className="form-error">{profileError}</p> : null}
        {fileError ? <p className="form-error">{fileError}</p> : null}

        <button className="form-submit" type="submit" disabled={isProcessing}>
          {isProcessing ? "Processing..." : "Find scholarships"}
        </button>
      </div>

      {hasSubmitted ? (
        <ProcessingState
          runId={processingRunId}
          onComplete={handleProcessingComplete}
          helperMessage={
            cvFile
              ? `CV attached: ${cvFile.name}. PDF parsing is not active in the frontend yet.`
              : "No CV attached. The profile text is enough to prepare recommendations."
          }
          completionMessage="Recommendations are ready below."
        />
      ) : (
        <section className="processing-card processing-card-idle" aria-label="Processing preview">
          <p className="terminal-label">terminal</p>
          <pre>{`$ waiting_for_profile
> submit your profile to start matching
> pdf upload: optional, kept for future backend handoff`}</pre>
        </section>
      )}

      {showResults ? <ScholarshipResults results={scholarshipResults} /> : null}
    </form>
  );
}

function buildSubmissionFormData(profileText: string, cvFile: File | null) {
  const formData = new FormData();
  formData.append("profile", profileText);

  if (cvFile) {
    formData.append("cv", cvFile);
  }

  return formData;
}
