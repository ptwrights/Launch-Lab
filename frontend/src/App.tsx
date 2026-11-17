
import { useEffect, useRef, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  CssBaseline,
  Dialog,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  LinearProgress,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import {
  AutoAwesome,
  CheckCircle,
  Close,
  Dashboard,
  Description,
  Download,
  PlayArrow,
  Search,
  Security,
  Visibility,
  UploadFile,
} from "@mui/icons-material";

import { ThemeProvider, createTheme } from "@mui/material/styles";

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const API_URL = "http://127.0.0.1:8000";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#64D6A0" },
    background: {
      default: "#081710",
      paper: "#12271D",
    },
    text: {
      primary: "#F0F7F2",
      secondary: "#A1B8A9",
    },
  },
  typography: {
    fontFamily: "Inter, Arial, sans-serif",
  },
  shape: {
    borderRadius: 14,
  },
});

type Regulation = "hipaa" | "ccpa";
type Source = Regulation | "uploaded";

type Page =
  | "Dashboard"
  | "Regulations"
  | "Detector Coverage"
  | "AI Insights";

type Filter = "all" | "full" | "partial" | "gaps";

type AnalysisResult = {
  regulation: string;
  entity: string;
  subcategories?: string[];
  regulatory_reference?: string;
  detector?: string | null;
  covered: boolean;
  status: string;
  source_text?: string;
  page?: number | null;
  source_excerpt?: string;
};

type AnalysisResults = AnalysisResult[];

function getStatus(
  item: AnalysisResult
): "full" | "partial" | "none" {
  if (item.covered === true) return "full";
  if (item.status === "Partial Detector Match") return "partial";
  return "none";
}

const statusInfo = {
  full: {
    label: "Full Match",
    color: "#64D6A0",
  },
  partial: {
    label: "Partial Match",
    color: "#F5BD65",
  },
  none: {
    label: "No Full Match",
    color: "#F08080",
  },
};

function App() {
  const [page, setPage] = useState<Page>("Dashboard");
  const [regulation, setRegulation] = useState<Regulation>("hipaa");
  const [source, setSource] = useState<Source>("hipaa");
  const [uploadedId, setUploadedId] = useState("");
  const [uploadedName, setUploadedName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadReady, setUploadReady] = useState(false);
  const uploadInput = useRef<HTMLInputElement | null>(null);
  const sourceLabel = source === "uploaded" ? (uploadedName || "Uploaded PDF") : source.toUpperCase();


  const [results, setResults] =
    useState<AnalysisResults | null>(null);

  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const busy = loading || analyzing || uploading;
  const [analysisComplete, setAnalysisComplete] = useState(false);

  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const [selected, setSelected] =
    useState<AnalysisResult | null>(null);

  const analysisInProgress = useRef(false);

  // Load existing report when changing regulation
  useEffect(() => {
    const controller = new AbortController();

    async function loadResults() {
      setLoading(true);
      setResults(null);
      setError("");
      setAnalysisComplete(false);
      setSearch("");
      setFilter("all");
      setSelected(null);

      if (source === "uploaded" && !uploadedId) {
        setLoading(false);
        return;
      }

      try {
        const endpoint = source === "uploaded"
          ? `${API_URL}/results-upload/${uploadedId}`
          : `${API_URL}/results/${source}`;
        const response = await fetch(endpoint, { signal: controller.signal });

        if (!response.ok) {
          // A newly uploaded PDF has no saved report until it is analyzed.
          if (source === "uploaded" && response.status === 404) return;
          throw new Error(`Could not load results (${response.status})`);
        }

        const data: unknown = await response.json();

        if (!Array.isArray(data)) {
          throw new Error("Invalid report format.");
        }

        if (!controller.signal.aborted) {
          setResults(data as AnalysisResults);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load results."
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadResults();

    return () => controller.abort();
  }, [source, uploadedId]);

  // Run real analysis through FastAPI
  async function handleRunAnalysis() {
    if (analysisInProgress.current) return;

    analysisInProgress.current = true;
    setAnalyzing(true);
    setAnalysisComplete(false);
    setError("");
    setSelected(null);

    try {
      if (source === "uploaded" && !uploadedId) {
        throw new Error("Upload a PDF before running analysis.");
      }
      const endpoint = source === "uploaded"
        ? `${API_URL}/analyze-upload/${uploadedId}`
        : `${API_URL}/analyze/${source}`;
      const response = await fetch(endpoint, { method: "POST" });

      if (!response.ok) {
        const details = await response.json().catch(() => null);

        throw new Error(
          details?.detail || `Analysis failed (${response.status})`
        );
      }

      const data: { results?: unknown } = await response.json();

      if (!Array.isArray(data.results)) {
        throw new Error("The backend returned an invalid report.");
      }

      setResults(data.results as AnalysisResults);
      setAnalysisComplete(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Analysis failed."
      );
    } finally {
      analysisInProgress.current = false;
      setAnalyzing(false);
    }
  }

  // Upload a PDF, then allow the user to run the real AI analysis.
  async function handleUpload(file: File | undefined) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setError("PDF must be 20 MB or smaller.");
      return;
    }

    setUploading(true);
    setError("");
    setAnalysisComplete(false);
    setResults(null);
    setUploadedId("");
    setUploadReady(false);
    setSource("uploaded");
    setSelected(null);
    setSearch("");
    setFilter("all");

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_URL}/upload-regulation`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Upload failed (${response.status})`);
      }
      if (typeof data.document_id !== "string") {
        throw new Error("Upload returned no document ID.");
      }
      setUploadedName(file.name);
      setUploadedId(data.document_id);
      setUploadReady(true);
      setPage("Regulations");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (uploadInput.current) uploadInput.current.value = "";
    }
  }

  // Live metrics
  const total = results?.length ?? 0;

  const full =
    results?.filter((item) => getStatus(item) === "full").length ?? 0;

  const partial =
    results?.filter((item) => getStatus(item) === "partial").length ?? 0;

  const unmatched = total - full - partial;
  const gaps = total - full;
  const uploadedMode = source === "uploaded";

  const matchRate = total
    ? Math.round((full / total) * 100)
    : 0;

  const metrics = [
    {
      label: "Sensitive Entities",
      value: total,
      icon: <Description />,
    },
    {
      label: "Detector Matches",
      value: full + partial,
      icon: <CheckCircle />,
    },
    {
      label: "Potential Gaps",
      value: gaps,
      icon: <Security />,
    },
    {
      label: uploadedMode ? "Detector Match Rate" : "Full Match Rate",
      value: `${matchRate}%`,
      icon: <AutoAwesome />,
    },
  ];

  const chartData = [
    {
      name: uploadedMode ? "Detector Match" : "Full Match",
      value: full,
      color: "#64D6A0",
    },
    {
      name: "Partial Match",
      value: partial,
      color: "#F5BD65",
    },
    {
      name: uploadedMode ? "No Detector Match" : "Unmatched",
      value: unmatched,
      color: "#F08080",
    },
  ].filter((item) => item.value > 0);

  const filteredResults = (results ?? []).filter((item) => {
    const status = getStatus(item);
    const query = search.toLowerCase();

    const searchableText = [
      item.entity,
      item.detector ?? "",
      item.regulatory_reference ?? "",
      ...(item.subcategories ?? []),
    ]
      .join(" ")
      .toLowerCase();

    const matchesSearch = searchableText.includes(query);

    const matchesFilter =
      filter === "all" ||
      (filter === "full" && status === "full") ||
      (filter === "partial" && status === "partial") ||
      (filter === "gaps" && status !== "full");

    return matchesSearch && matchesFilter;
  });

  const gapResults = (results ?? []).filter(
    (item) => getStatus(item) !== "full"
  );

  function handleExportReport() {
    if (!results) return;

    const report = {
      report_name: "GapGuard AI Detector Coverage Report",
      regulation: sourceLabel,
      document_id: uploadedMode ? uploadedId : undefined,
      exported_at: new Date().toISOString(),
      summary: {
        total_sensitive_entities: total,
        full_detector_matches: full,
        partial_detector_matches: partial,
        unmatched_entities: unmatched,
        potential_gaps: gaps,
        full_match_rate_percent: matchRate,
      },
      detector_coverage_results: results,
      disclaimer:
        "This report uses a simulated detector inventory. " +
        "Results do not establish legal compliance or " +
        "verified NetApp detector coverage.",
    };

    const blob = new Blob(
      [JSON.stringify(report, null, 2)],
      { type: "application/json" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `gapguard_${uploadedMode ? uploadedId : regulation}_report.json`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // Shared regulation selector and analysis controls
  const analysisControls = (
    <Card sx={{ mb: 3 }}>
      <CardContent
        sx={{
          p: 3,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 2,
          flexWrap: "wrap",
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: "bold" }}>
            Regulation Analysis
          </Typography>
          <Typography color="text.secondary" sx={{ fontSize: 14 }}>
            Select a regulation or upload a PDF, then analyze and export results.
          </Typography>
        </Box>

        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <FormControl size="small">
            <Select
              value={source}
              disabled={busy}
              onChange={(event) => {
                const value = event.target.value as Source;
                setSource(value);
                if (value !== "uploaded") setRegulation(value);
              }}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="hipaa">HIPAA</MenuItem>
              <MenuItem value="ccpa">CCPA</MenuItem>
             {uploadedId ? (
  <MenuItem value="uploaded">Uploaded PDF</MenuItem>
) : null}
            </Select>
          </FormControl>

          <input
            ref={uploadInput}
            type="file"
            accept=".pdf,application/pdf"
            style={{ display: "none" }}
            onChange={(event) => void handleUpload(event.target.files?.[0])}
          />
          <Button
            variant="outlined"
            startIcon={uploading ? <CircularProgress size={17} /> : <UploadFile />}
            disabled={busy}
            onClick={() => uploadInput.current?.click()}
          >
            {uploading ? "Uploading..." : "Upload PDF"}
          </Button>

          <Button
            variant="contained"
            startIcon={
              analyzing ? (
                <CircularProgress size={17} color="inherit" />
              ) : (
                <PlayArrow />
              )
            }
            disabled={busy || (uploadedMode && !uploadedId)}
            onClick={handleRunAnalysis}
          >
            {analyzing ? "Analyzing..." : "Run Analysis"}
          </Button>

          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={handleExportReport}
            disabled={!results || busy}
          >
            Export Report
          </Button>
        </Box>
      </CardContent>
    </Card>
  );

  // Shared coverage chart
  const coverageChart = (
    <Card sx={{ mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: "bold", mb: 1 }}>
          Detector Coverage Breakdown
        </Typography>

        <Typography color="text.secondary" sx={{ fontSize: 14 }}>
          Current {sourceLabel} detector mapping results. {uploadedMode && "Matches are candidate detector capabilities, not full regulatory coverage."}
        </Typography>

        {results && total > 0 ? (
          <Box sx={{ width: "100%", height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={70}
                  outerRadius={105}
                  paddingAngle={3}
                >
                  {chartData.map((item) => (
                    <Cell key={item.name} fill={item.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Box>
        ) : (
          <Typography color="text.secondary" sx={{ py: 5 }}>
            No chart data available.
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  // Shared evidence explorer
  const coverageExplorer = (
    <Card sx={{ mb: 3 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: "bold", mb: 1 }}>
          Detector Coverage Explorer
        </Typography>

        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Search, filter, and inspect detector mapping evidence.
        </Typography>

        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
          <TextField
            size="small"
            placeholder="Search entities or detectors..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            slotProps={{
              input: {
                startAdornment: (
                  <Search sx={{ color: "#A1B8A9", mr: 1 }} />
                ),
              },
            }}
            sx={{ flex: 1, minWidth: 220 }}
          />

          <FormControl size="small" sx={{ minWidth: 170 }}>
            <Select
              value={filter}
              onChange={(event) =>
                setFilter(event.target.value as Filter)
              }
            >
              <MenuItem value="all">All Entities</MenuItem>
              <MenuItem value="full">Full Matches</MenuItem>
              <MenuItem value="partial">Partial Matches</MenuItem>
              <MenuItem value="gaps">Potential Gaps</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Typography color="text.secondary" sx={{ fontSize: 13, mb: 2 }}>
          Showing {filteredResults.length} of {total} entities
        </Typography>

        <TableContainer sx={{ maxHeight: 480 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell>Entity</TableCell>
                <TableCell>Detector</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Evidence</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {filteredResults.map((item, index) => {
                 const info = uploadedMode && item.covered
                   ? { label: "Detector Match", color: "#64D6A0" }
                   : uploadedMode
                   ? { label: "No Detector Match", color: "#F08080" }
                   : statusInfo[getStatus(item)];

                return (
                  <TableRow
                    key={`${item.entity}-${index}`}
                    hover
                    sx={{ cursor: "pointer" }}
                    onClick={() => setSelected(item)}
                  >
                    <TableCell sx={{ fontWeight: 600 }}>
                      {item.entity}
                    </TableCell>

                    <TableCell>
                      {item.detector || "No detector mapped"}
                    </TableCell>

                    <TableCell>
                      <Chip
                        size="small"
                        label={info.label}
                        sx={{
                          color: info.color,
                          border: `1px solid ${info.color}`,
                          bgcolor: "transparent",
                        }}
                      />
                    </TableCell>

                    <TableCell align="right">
                      <IconButton
                        size="small"
                        aria-label={`View evidence for ${item.entity}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelected(item);
                        }}
                      >
                        <Visibility fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {filteredResults.length === 0 && (
          <Typography
            color="text.secondary"
            sx={{ textAlign: "center", py: 4 }}
          >
            No entities match your search or filter.
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      <Box sx={{ display: "flex", minHeight: "100vh" }}>
        {/* Sidebar */}
        <Box
          sx={{
            width: 240,
            flexShrink: 0,
            bgcolor: "#0D2016",
            borderRight: "1px solid #244334",
            p: 3,
            display: { xs: "none", md: "block" },
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 6 }}>
            <Security sx={{ color: "#64D6A0", fontSize: 32 }} />
            <Typography variant="h5" sx={{ fontWeight: "bold" }}>
              GapGuard AI
            </Typography>
          </Box>

          <Typography color="text.secondary" sx={{ fontSize: 12, mb: 2 }}>
            WORKSPACE
          </Typography>

          {[
            { name: "Dashboard" as Page, icon: <Dashboard /> },
            { name: "Regulations" as Page, icon: <Description /> },
            { name: "Detector Coverage" as Page, icon: <Security /> },
            { name: "AI Insights" as Page, icon: <AutoAwesome /> },
          ].map((item) => (
            <Button
              key={item.name}
              fullWidth
              startIcon={item.icon}
              onClick={() => setPage(item.name)}
              sx={{
                justifyContent: "flex-start",
                textTransform: "none",
                mb: 1,
                p: 1.5,
                color: page === item.name ? "#64D6A0" : "#A1B8A9",
                bgcolor: page === item.name ? "#1A3A29" : "transparent",
                "&:hover": {
                  bgcolor: "#1A3A29",
                },
              }}
            >
              {item.name}
            </Button>
          ))}
        </Box>

        {/* Main content */}
        <Box
          component="main"
          sx={{ flex: 1, minWidth: 0, p: { xs: 2, md: 5 } }}
        >
          <Typography
            color="primary"
            sx={{ fontSize: 13, fontWeight: "bold", letterSpacing: 1.5 }}
          >
            REGULATORY INTELLIGENCE PLATFORM
          </Typography>

          <Typography variant="h3" sx={{ fontWeight: "bold", mt: 1 }}>
            {page === "Dashboard" ? "Security Overview" : page}
          </Typography>

          <Typography color="text.secondary" sx={{ mt: 1, mb: 4 }}>
            {page === "Dashboard"
              ? "Analyze regulations. Identify sensitive data. Discover gaps."
              : page === "Regulations"
              ? "Manage regulatory analyses and download reports."
              : page === "Detector Coverage"
              ? "Explore detector matches and inspect regulatory evidence."
              : "Review potential coverage gaps and supporting evidence."}
          </Typography>

          {/* Controls visible on all pages */}
          {analysisControls}

          {analyzing && (
            <Alert severity="info" sx={{ mb: 3 }}>
              GapGuard AI is analyzing {sourceLabel}.
              This may take a few minutes.
              <LinearProgress sx={{ mt: 2 }} />
            </Alert>
          )}

          {analysisComplete && !analyzing && (
            <Alert severity="success" sx={{ mb: 3 }}>
              AI analysis completed successfully.
              Your {sourceLabel} results have been refreshed.
            </Alert>
          )}

          {uploadReady && uploadedMode && !analyzing && !analysisComplete && !results && !error && (
            <Alert severity="success" sx={{ mb: 3 }}>
              {uploadedName} uploaded successfully. Click Run Analysis to analyze its contents.
            </Alert>
          )}

          {loading && (
            <Alert severity="info" sx={{ mb: 3 }}>
              Loading saved results...
            </Alert>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {/* Dashboard */}
          {page === "Dashboard" && (
            <>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2, 1fr)",
                    lg: "repeat(4, 1fr)",
                  },
                  gap: 2,
                  mb: 3,
                }}
              >
                {metrics.map((metric) => (
                  <Card key={metric.label}>
                    <CardContent sx={{ p: 3 }}>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <Typography
                          color="text.secondary"
                          sx={{ fontSize: 13 }}
                        >
                          {metric.label}
                        </Typography>

                        <Box sx={{ color: "#64D6A0" }}>
                          {metric.icon}
                        </Box>
                      </Box>

                      <Typography
                        variant="h3"
                        color="primary"
                        sx={{ fontWeight: "bold", mt: 2 }}
                      >
                        {results ? metric.value : "—"}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Box>

              {coverageChart}
            </>
          )}

          {/* Regulations */}
          {page === "Regulations" && (
            <Card sx={{ mb: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: "bold", mb: 2 }}>
                  Available Regulations
                </Typography>

                <Box sx={{ mb: 3, p: 2, border: "1px solid #244334", borderRadius: 2 }}>
                  <Typography variant="h6" sx={{ mb: 1 }}>Upload a Regulation</Typography>
                  <Typography color="text.secondary" sx={{ mb: 2 }}>
                    Upload a text-based PDF (up to 20 MB) and analyze its sensitive data categories using Ollama and hybrid retrieval.
                  </Typography>
                  <Button variant="outlined" startIcon={<UploadFile />} disabled={busy}
                    onClick={() => uploadInput.current?.click()}>
                    Choose PDF
                  </Button>
                  {uploadedId && <Typography sx={{ mt: 2 }} color="text.secondary">
                    Uploaded: {uploadedName} — {uploadedMode ? "Selected" : "Available in selector"}
                  </Typography>}
                </Box>

                {(["hipaa", "ccpa"] as Regulation[]).map((item) => (
                  <Box
                    key={item}
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      p: 2,
                      mb: 2,
                      border: "1px solid #244334",
                      borderRadius: 2,
                      gap: 2,
                      flexWrap: "wrap",
                    }}
                  >
                    <Box>
                      <Typography sx={{ fontWeight: "bold" }}>
                        {item.toUpperCase()}
                      </Typography>

                      <Typography
                        color="text.secondary"
                        sx={{ fontSize: 13 }}
                      >
                        {item === "hipaa"
                          ? "Health Insurance Portability and Accountability Act"
                          : "California Consumer Privacy Act"}
                      </Typography>
                    </Box>

                    <Button
                      variant={source === item ? "contained" : "outlined"}
                      disabled={busy}
                      onClick={() => { setRegulation(item); setSource(item); }}
                    >
                      {source === item ? "Selected" : "Select"}
                    </Button>
                  </Box>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Detector Coverage */}
          {page === "Detector Coverage" && (
            <>
              {coverageChart}
              {coverageExplorer}
            </>
          )}

          {/* AI Insights */}
          {page === "AI Insights" && (
            <>
              <Card sx={{ mb: 3 }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography
                    variant="h6"
                    sx={{ fontWeight: "bold", mb: 2 }}
                  >
                    Coverage Gap Summary
                  </Typography>

                  {results ? (
                    <>
                      <Typography color="text.secondary" sx={{ mb: 2 }}>
                        {sourceLabel} analysis identified{" "}
                        <strong>{gaps} potential gaps</strong> across{" "}
                        {total} sensitive entities.
                      </Typography>

                      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                        <Chip
                          label={`${full} ${uploadedMode ? "Detector Matches" : "Full Matches"}`}
                          color="success"
                          variant="outlined"
                        />
                        <Chip
                          label={`${partial} Partial Matches`}
                          color="warning"
                          variant="outlined"
                        />
                        <Chip
                          label={`${unmatched} Unmatched`}
                          color="error"
                          variant="outlined"
                        />
                      </Box>
                    </>
                  ) : (
                    <Typography color="text.secondary">
                      No analysis results available.
                    </Typography>
                  )}
                </CardContent>
              </Card>

              <Typography
                variant="h6"
                sx={{ fontWeight: "bold", mb: 2 }}
              >
                Findings Requiring Review
              </Typography>

              {gapResults.map((item, index) => {
                const status = getStatus(item);

                return (
                  <Card
                    key={`${item.entity}-${index}`}
                    sx={{ mb: 2 }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: 2,
                          flexWrap: "wrap",
                          mb: 2,
                        }}
                      >
                        <Typography
                          variant="h6"
                          sx={{ fontWeight: "bold" }}
                        >
                          {item.entity}
                        </Typography>

                        <Chip
                          label={uploadedMode ? "No Detector Match" : statusInfo[status].label}
                          size="small"
                          sx={{
                            color: statusInfo[status].color,
                            border: `1px solid ${statusInfo[status].color}`,
                          }}
                        />
                      </Box>

                      <Typography color="text.secondary" sx={{ mb: 1 }}>
                        Detector: {item.detector || "No detector mapped"}
                      </Typography>

                      <Typography color="text.secondary" sx={{ mb: 2 }}>
                        Reference:{" "}
                        {item.regulatory_reference || "Not available"}
                      </Typography>

                      <Button
                        variant="outlined"
                        startIcon={<Visibility />}
                        onClick={() => setSelected(item)}
                      >
                        View Evidence
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}

              {results && gapResults.length === 0 && (
                <Typography color="text.secondary">
                  No potential gaps were identified in this report.
                </Typography>
              )}
            </>
          )}

          {/* Evidence popup shared across pages */}
          <Dialog
            open={selected !== null}
            onClose={() => setSelected(null)}
            fullWidth
            maxWidth="sm"
          >
            {selected && (
              <>
                <DialogTitle
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  {selected.entity}

                  <IconButton onClick={() => setSelected(null)}>
                    <Close />
                  </IconButton>
                </DialogTitle>

                <DialogContent dividers>
                  <Chip
                    label={uploadedMode
                      ? (selected.covered ? "Detector Match" : "No Detector Match")
                      : statusInfo[getStatus(selected)].label}
                    variant="outlined"
                    sx={{
                      color: statusInfo[getStatus(selected)].color,
                      mb: 3,
                    }}
                  />

                  <Typography color="text.secondary" sx={{ fontSize: 13 }}>
                    Mapped Detector
                  </Typography>

                  <Typography sx={{ mb: 3 }}>
                    {selected.detector || "No detector mapped"}
                  </Typography>

                  <Typography color="text.secondary" sx={{ fontSize: 13 }}>
                    Regulatory Reference
                  </Typography>

                  <Typography sx={{ mb: 3 }}>
                    {selected.regulatory_reference || "Not available"}
                  </Typography>

                  <Typography color="text.secondary" sx={{ fontSize: 13 }}>
                    Source Page
                  </Typography>

                  <Typography sx={{ mb: 3 }}>
                    {selected.page ?? "Not available"}
                  </Typography>

                  <Typography color="text.secondary" sx={{ fontSize: 13 }}>
                    Source Evidence
                  </Typography>

                  <Box
                    sx={{
                      p: 2,
                      mt: 1,
                      mb: 3,
                      bgcolor: "#081710",
                      borderRadius: 2,
                      whiteSpace: "pre-wrap",
                      overflowWrap: "anywhere",
                    }}
                  >
                    {selected.source_excerpt ||
                      selected.source_text ||
                      "No source excerpt available."}
                  </Box>

                  {selected.subcategories &&
                    selected.subcategories.length > 0 && (
                      <>
                        <Typography
                          color="text.secondary"
                          sx={{ fontSize: 13, mb: 1 }}
                        >
                          Subcategories
                        </Typography>

                        <Box
                          sx={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 1,
                          }}
                        >
                          {selected.subcategories.map((category) => (
                            <Chip
                              key={category}
                              label={category}
                              size="small"
                              variant="outlined"
                            />
                          ))}
                        </Box>
                      </>
                    )}
                </DialogContent>
              </>
            )}
          </Dialog>

          <Typography
            color="text.secondary"
            sx={{ fontSize: 12, mt: 4, textAlign: "center" }}
          >
            GapGuard AI • Prototype using a simulated detector inventory.
            Results do not establish legal compliance or verified NetApp
            detector coverage.
          </Typography>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;






