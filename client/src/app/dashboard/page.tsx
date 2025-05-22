"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useJob } from "@/lib/job-context";
import { fetchPersonas, type Celebrity } from "@/lib/api";
import Image from "next/image";

// Shadcn UI & Lucide Icons
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Loader2,
  AlertCircle,
  Brain,
  Search,
  CheckCircle,
  Sparkles,
  ChevronRight,
  MessageSquareText,
  Info,
  Star,
  Lightbulb,
  ArrowRight,
  Music,
  Mic,
  Tv,
} from "lucide-react";

// Celebrity Card Component
interface CelebrityCardProps {
  celebrity: Celebrity;
  isSelected: boolean;
  onSelect: (celebrity: Celebrity) => void;
  disabled: boolean;
}

const CelebrityCard: React.FC<CelebrityCardProps> = ({
  celebrity,
  isSelected,
  onSelect,
  disabled,
}) => {
  return (
    <div
      onClick={() => !disabled && onSelect(celebrity)}
      className={`
        group relative rounded-2xl overflow-hidden transition-all duration-300 ease-out cursor-pointer 
        ${disabled ? "opacity-50 cursor-not-allowed grayscale" : ""}
      `}
    >
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent z-10"></div>

      {/* Selection indicator ring */}
      <div
        className={`absolute inset-0 border-2 rounded-2xl z-20 transition-all duration-300 ${
          isSelected
            ? "border-purple-500 scale-[0.98]"
            : "border-transparent scale-100"
        }`}
      ></div>

      {/* Image background */}
      <div className="w-full aspect-[4/5] relative">
        <Image
          src={celebrity.image}
          alt={celebrity.name}
          fill
          className={`object-cover transition-all duration-500 ${
            isSelected
              ? "scale-105 brightness-110"
              : "group-hover:scale-105 group-hover:brightness-105"
          }`}
        />
      </div>

      {/* Content overlay */}
      <div className="absolute bottom-0 left-0 right-0 p-4 z-30">
        <div className="flex items-end justify-between">
          <div>
            <h3 className="font-semibold text-base sm:text-lg text-white mb-1 tracking-wide">
              {celebrity.name}
            </h3>
            <p className="text-xs text-purple-200/80 font-medium">AI Persona</p>
          </div>

          {/* Selection indicator */}
          <div
            className={`
            h-8 w-8 rounded-full flex items-center justify-center transition-all duration-300
            ${
              isSelected
                ? "bg-purple-600 text-white"
                : "bg-white/10 backdrop-blur-sm text-white/70 opacity-0 group-hover:opacity-100"
            }
          `}
          >
            {isSelected ? (
              <CheckCircle size={16} className="text-white" />
            ) : (
              <Star size={16} />
            )}
          </div>
        </div>
      </div>

      {/* Selected badge */}
      {isSelected && (
        <div className="absolute top-3 right-3 bg-purple-600 text-white text-xs font-medium py-1 px-2.5 rounded-full z-20 shadow-lg">
          Selected
        </div>
      )}
    </div>
  );
};

export default function DashboardPage() {
  const [selectedCelebrity, setSelectedCelebrity] = useState<Celebrity | null>(
    null
  );
  const [topic, setTopic] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [celebrities, setCelebrities] = useState<Celebrity[]>([]);
  const [loadingCelebrities, setLoadingCelebrities] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  const { clearJob, createNewJob } = useJob();
  const router = useRouter();

  useEffect(() => {
    const loadCelebrities = async () => {
      setLoadingCelebrities(true);
      setLoadError(null);
      try {
        const data = await fetchPersonas();
        setCelebrities(data);
      } catch (err) {
        setLoadError(
          err instanceof Error ? err.message : "Failed to load personas"
        );
        console.error("Error loading personas:", err);
      } finally {
        setLoadingCelebrities(false);
      }
    };
    loadCelebrities();
  }, []);

  const filteredCelebrities = celebrities.filter((celeb) =>
    celeb.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleGenerate = async () => {
    if (!selectedCelebrity || !topic.trim() || isSubmitting) return;
    setIsSubmitting(true);
    setLoadError(null);
    try {
      clearJob();
      const newJob = await createNewJob(topic.trim(), selectedCelebrity.id);
      router.push(`/results/${newJob.job_id}`);
    } catch (error) {
      console.error("Error creating job:", error);
      setLoadError("Failed to start explanation generation. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const canSubmit = selectedCelebrity && topic.trim() && !isSubmitting;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-950/70 to-slate-900 text-white">
      {/* Top decorative element */}
      <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-purple-500 via-pink-400 to-purple-500"></div>

      {/* Background effects */}
      <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-purple-500/15 blur-[120px] -z-10"></div>
      <div className="absolute bottom-10 right-1/4 w-[400px] h-[400px] rounded-full bg-pink-500/15 blur-[100px] -z-10"></div>

      {/* Main content */}
      <div className="w-full max-w-screen-xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Header with logo */}
        <header className="flex items-center justify-between mb-10 sm:mb-16">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="absolute inset-0 bg-purple-500 rounded-full blur-sm opacity-60"></div>
              <div className="relative bg-gradient-to-br from-purple-500 to-purple-700 p-2.5 rounded-full">
                <Brain className="h-6 w-6 text-white" />
              </div>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
              Spew
            </h1>
          </div>

          <nav>
            <Button
              variant="outline"
              size="sm"
              className="text-sm bg-transparent border-purple-400/40 text-purple-100 hover:bg-purple-500/20"
            >
              <ArrowRight className="h-3.5 w-3.5 mr-1.5" />
              Exit Studio
            </Button>
          </nav>
        </header>

        {/* Page heading */}
        <div className="text-center mb-10 sm:mb-16">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white via-purple-100 to-white">
            Celebrity Meme Learning Studio
          </h1>
          <p className="text-purple-100 text-lg max-w-2xl mx-auto font-light">
            Select a persona and topic to create your personalized explanation
            video
          </p>
        </div>

        {/* Main two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 mb-10">
          {/* Persona selection - Larger left column */}
          <div className="lg:col-span-3 space-y-6">
            <div className="bg-slate-800/80 backdrop-blur-sm rounded-2xl border border-purple-500/20 overflow-hidden shadow-xl">
              <div className="p-6 sm:p-8">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="bg-purple-500/20 p-2 rounded-lg">
                      <Mic className="h-5 w-5 text-purple-300" />
                    </div>
                    <h2 className="text-xl font-medium text-white">
                      Choose Your Persona
                    </h2>
                  </div>

                  {/* Search bar */}
                  <div className="relative w-full max-w-[220px]">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-purple-300/60" />
                    <Input
                      type="text"
                      placeholder="Search personas..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-9 py-2 text-sm bg-slate-700/60 border-purple-500/20 focus:border-purple-500 rounded-lg text-white"
                      disabled={loadingCelebrities || isSubmitting}
                    />
                  </div>
                </div>

                {/* Loading state */}
                {loadingCelebrities && (
                  <div className="flex flex-col items-center justify-center text-purple-200 py-20">
                    <Loader2 className="h-8 w-8 animate-spin mb-4 text-purple-400" />
                    <p className="text-purple-200 font-medium">
                      Loading personas...
                    </p>
                    <Progress
                      value={65}
                      className="w-48 h-1 mt-4 bg-purple-900/30"
                    />
                  </div>
                )}

                {/* Celebrity grid */}
                {!loadingCelebrities &&
                  celebrities.length > 0 &&
                  filteredCelebrities.length > 0 && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-5">
                      {filteredCelebrities.map((celeb) => (
                        <CelebrityCard
                          key={celeb.id}
                          celebrity={celeb}
                          isSelected={selectedCelebrity?.id === celeb.id}
                          onSelect={setSelectedCelebrity}
                          disabled={isSubmitting}
                        />
                      ))}
                    </div>
                  )}

                {/* No results state */}
                {!loadingCelebrities &&
                  celebrities.length > 0 &&
                  filteredCelebrities.length === 0 && (
                    <Alert className="bg-slate-700/60 border border-purple-500/20 text-center py-8">
                      <Search className="h-5 w-5 mx-auto mb-3 text-purple-300/60" />
                      <AlertTitle className="text-white font-medium text-base mb-1">
                        No Matching Personas
                      </AlertTitle>
                      <AlertDescription className="text-purple-200/80 text-sm">
                        No personas found for "{searchTerm}". Try a different
                        search.
                      </AlertDescription>
                    </Alert>
                  )}

                {/* No personas available state */}
                {!loadingCelebrities &&
                  celebrities.length === 0 &&
                  !loadError && (
                    <Alert className="bg-slate-700/60 border border-purple-500/20 text-center py-8">
                      <AlertTitle className="text-white font-medium text-base mb-1">
                        No Personas Available
                      </AlertTitle>
                      <AlertDescription className="text-purple-200/80 text-sm">
                        Check back later or ensure personas are loaded
                        correctly.
                      </AlertDescription>
                    </Alert>
                  )}
              </div>
            </div>
          </div>

          {/* Topic input and action - Smaller right column */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-800/80 backdrop-blur-sm rounded-2xl border border-purple-500/20 overflow-hidden h-full shadow-xl">
              <div className="p-6 sm:p-8 flex flex-col h-full">
                <div className="flex items-center gap-3 mb-6">
                  <div className="bg-purple-500/20 p-2 rounded-lg">
                    <Lightbulb className="h-5 w-5 text-purple-300" />
                  </div>
                  <h2 className="text-xl font-medium text-white">
                    Enter Your Topic
                  </h2>
                </div>

                {/* Topic input */}
                <div className="relative mb-6">
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 opacity-70 blur-sm"></div>
                  <div className="relative bg-slate-800 rounded-xl p-1">
                    <textarea
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder={
                        selectedCelebrity
                          ? `What should ${selectedCelebrity.name} explain to you?`
                          : "Select a persona first, then enter your topic here..."
                      }
                      disabled={isSubmitting || !selectedCelebrity}
                      className="w-full min-h-[120px] p-4 bg-slate-700/60 rounded-lg text-white placeholder:text-purple-300/50 resize-none border-0 focus:ring-0 focus:outline-none disabled:opacity-50"
                    />
                  </div>
                </div>

                {/* Info box */}
                {selectedCelebrity ? (
                  <div className="flex items-start gap-3 mb-8 bg-purple-500/10 rounded-xl p-4 border border-purple-500/20">
                    <Info className="h-5 w-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-purple-100">
                        {topic.trim()
                          ? `${selectedCelebrity.name} will explain "${topic}" in their unique style.`
                          : `What would you like ${selectedCelebrity.name} to explain today?`}
                      </p>
                      <p className="text-xs text-purple-300/80 mt-1">
                        Try specific questions for better results. The more
                        detailed, the better!
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-3 mb-8 bg-purple-500/5 rounded-xl p-4 border border-purple-500/10">
                    <Info className="h-5 w-5 text-purple-400/50 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm text-purple-200/90">
                        Select a persona from the left to continue
                      </p>
                      <p className="text-xs text-purple-300/60 mt-1">
                        Each persona has their own unique explanation style
                      </p>
                    </div>
                  </div>
                )}

                {/* Action buttons */}
                <div className="mt-auto">
                  {/* Error alert */}
                  {loadError && (
                    <Alert
                      variant="destructive"
                      className="mb-4 bg-red-500/10 border-red-500/30"
                    >
                      <AlertCircle className="h-4 w-4 text-red-400" />
                      <AlertTitle>Error</AlertTitle>
                      <AlertDescription>{loadError}</AlertDescription>
                    </Alert>
                  )}

                  {/* Generate button */}
                  <Button
                    onClick={handleGenerate}
                    disabled={!canSubmit}
                    className={`
                      w-full py-6 rounded-xl text-base font-medium 
                      ${
                        canSubmit
                          ? "bg-gradient-to-r from-purple-500 via-pink-500 to-purple-500 hover:from-purple-400 hover:via-pink-400 hover:to-purple-400 shadow-lg shadow-purple-500/20"
                          : "bg-purple-500/20 text-purple-200/50"
                      }
                      transition-all duration-300 relative overflow-hidden group
                    `}
                  >
                    {/* Button background animation */}
                    {canSubmit && (
                      <div className="absolute inset-0 bg-gradient-to-r from-purple-600/0 via-white/30 to-purple-600/0 -translate-x-full group-hover:translate-x-full transition-all duration-1000 ease-in-out"></div>
                    )}

                    {/* Button content */}
                    <span className="relative flex items-center justify-center">
                      {isSubmitting ? (
                        <>
                          <Loader2 className="animate-spin h-5 w-5 mr-2" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-5 w-5 mr-2 group-hover:scale-110 transition-transform duration-300" />
                          Create Explanation Video
                          <ChevronRight className="ml-1.5 h-5 w-5 group-hover:translate-x-1 transition-transform duration-300" />
                        </>
                      )}
                    </span>
                  </Button>

                  {isSubmitting && (
                    <p className="text-center text-purple-300/60 text-sm mt-4">
                      This may take a few moments...
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Features section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/10 p-5 flex shadow-lg">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mr-4 flex-shrink-0">
              <MessageSquareText className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">
                Personalized Learning
              </h3>
              <p className="text-sm text-purple-200/90">
                Celebrity-style explanations make complex topics entertaining
                and memorable
              </p>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/10 p-5 flex shadow-lg">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mr-4 flex-shrink-0">
              <Tv className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Instant Videos</h3>
              <p className="text-sm text-purple-200/90">
                Generate entertaining explanation videos in seconds with AI
                technology
              </p>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/10 p-5 flex shadow-lg">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mr-4 flex-shrink-0">
              <Music className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="font-medium text-white mb-1">Meme-Worthy Style</h3>
              <p className="text-sm text-purple-200/90">
                Share fun yet educational content with unique celebrity
                personalities
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center">
          <p className="text-xs text-purple-300/60">
            &copy; {new Date().getFullYear()} Spew AI | The Celebrity Meme
            Learning Studio
          </p>
        </footer>
      </div>
    </div>
  );
}
