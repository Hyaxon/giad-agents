package agents

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/hyaxon/giad/internal/model"
	"github.com/hyaxon/giad/internal/sandbox"
	"github.com/hyaxon/giad/internal/tools"
	"github.com/hyaxon/giad/pkg/protocol"
)

// This file is overlaid into the runtime package by tools/giad_smoke.py.
type officialProvider struct {
	answers  []string
	plan     []protocol.ToolCall
	planned  bool
	chats    int
	unloads  int
	messages []model.Message
}

func (p *officialProvider) Chat(_ context.Context, _ string, messages []model.Message, _ []model.Tool) (model.Message, error) {
	p.messages = messages
	if len(p.plan) > 0 && !p.planned {
		p.planned = true
		p.chats++
		return model.Message{Role: "assistant", ToolCalls: p.plan}, nil
	}
	offset := 0
	if p.planned {
		offset = 1
	}
	if p.chats-offset >= len(p.answers) {
		return model.Message{}, errors.New("fixture model unavailable")
	}
	answer := p.answers[p.chats-offset]
	p.chats++
	return model.Message{Role: "assistant", Content: answer}, nil
}

func (p *officialProvider) Unload(context.Context, string) error {
	p.unloads++
	return nil
}

func TestOfficialAgents(t *testing.T) {
	root := os.Getenv("GIAD_OFFICIAL_AGENTS_ROOT")
	if root == "" {
		t.Fatal("run through tools/giad_smoke.py")
	}
	finding := protocol.Finding{
		Source: "code-review", Category: "correctness", File: "add.py", Line: 2,
		Severity: "high", Confidence: .9, Title: "Addition subtracts instead",
		Explanation: "The changed return value subtracts b.", Evidence: "return a - b",
		FailureScenario: "add(2, 3) returns -1 instead of 5.", SuggestedFix: "Return a + b.",
	}
	data, err := json.Marshal(protocol.Report{Summary: "Inspected addition", Limitations: "No callers inspected.", Findings: []protocol.Finding{finding}})
	if err != nil {
		t.Fatal(err)
	}
	good := string(data)
	clean := `{"summary":"Inspected addition","limitations":"No callers inspected.","findings":[]}`
	for _, tc := range []struct {
		name         string
		agent        string
		answers      []string
		wantFindings int
		wantFailure  bool
		truncated    bool
		tests        bool
		broad        bool
	}{
		{name: "metadata", agent: "pr-summary"},
		{name: "diff", agent: "diff-inspector"},
		{name: "truncated diff", agent: "diff-inspector", truncated: true},
		{name: "anchored finding", agent: "code-review", answers: []string{good}, wantFindings: 1},
		{name: "clean report", agent: "code-review", answers: []string{clean}},
		{name: "fenced report", agent: "code-review", answers: []string{"```json\n" + good + "\n```"}, wantFindings: 1},
		{name: "repair severity", agent: "code-review", answers: []string{strings.Replace(good, `"high"`, `"critical"`, 1), good}, wantFindings: 1},
		{name: "malformed model", agent: "code-review", answers: []string{"not JSON", "not JSON"}, wantFailure: true},
		{name: "unread anchor", agent: "code-review", answers: []string{strings.Replace(good, `"line":2`, `"line":999`, 1), strings.Replace(good, `"line":2`, `"line":999`, 1)}, wantFailure: true},
		{name: "model unavailable", agent: "code-review", wantFailure: true},
		{name: "head test evidence", agent: "code-review", answers: []string{clean}, tests: true},
		{name: "whole PR later lines and dependencies", agent: "code-review", broad: true, wantFindings: 5},
		{name: "test summary", agent: "test-summary", tests: true},
		{name: "test summary requires approved profiles", agent: "test-summary", wantFailure: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			manifest, err := LoadManifest(filepath.Join(root, "agents", tc.agent, "agent.manifest.json"))
			if err != nil {
				t.Fatal(err)
			}
			var launcher sandbox.Launcher = sandbox.TrustedHostLauncher{}
			if image := os.Getenv("GIAD_OFFICIAL_IMAGE"); image != "" {
				launcher = sandbox.DockerLauncher{Image: image}
			} else {
				// The trusted host launcher intentionally strips environment variables.
				pathJSON, _ := json.Marshal(filepath.Join(root, "src"))
				moduleJSON, _ := json.Marshal("giad_agents." + strings.ReplaceAll(tc.agent, "-", "_"))
				manifest.Entrypoint = protocol.Entrypoint{Command: os.Getenv("GIAD_OFFICIAL_PYTHON"), Args: []string{"-c", "import sys,runpy; sys.path.insert(0," + string(pathJSON) + "); runpy.run_module(" + string(moduleJSON) + ",run_name='__main__')"}}
			}
			grants, err := Grants(manifest, append(append([]string{}, manifest.Capabilities.Required...), manifest.Capabilities.Optional...))
			if err != nil {
				t.Fatal(err)
			}
			checkout := t.TempDir()
			if err := os.WriteFile(filepath.Join(checkout, "add.py"), []byte("def add(a, b):\n    return a - b\n"), 0600); err != nil {
				t.Fatal(err)
			}
			diff := "diff --git a/add.py b/add.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a + b\n+    return a - b\n"
			if tc.truncated {
				diff += strings.Repeat("x", 70*1024)
			}
			reader, err := tools.Open(checkout, diff)
			if err != nil {
				t.Fatal(err)
			}
			defer reader.Close()
			provider := &officialProvider{answers: tc.answers}
			if tc.agent == "code-review" {
				provider.plan = []protocol.ToolCall{{Function: protocol.CallFunction{Name: "repository_read", Arguments: json.RawMessage(`{"path":"add.py","start":1,"end":0}`)}}}
				if tc.tests {
					provider.plan = append(provider.plan, protocol.ToolCall{Function: protocol.CallFunction{Name: "tests_run", Arguments: json.RawMessage(`{"profile":"unit"}`)}})
				}
				if tc.broad {
					provider.plan = nil
					findings := []protocol.Finding{}
					for i := 0; i < 5; i++ {
						path := "file" + string(rune('0'+i)) + ".py"
						args, _ := json.Marshal(map[string]any{"path": path, "start": 180, "end": 0})
						provider.plan = append(provider.plan, protocol.ToolCall{Function: protocol.CallFunction{Name: "repository_read", Arguments: args}})
						f := finding
						f.File, f.Line = "file4.py", 180+i
						findings = append(findings, f)
					}
					provider.plan = append(provider.plan,
						protocol.ToolCall{Function: protocol.CallFunction{Name: "repository_search", Arguments: json.RawMessage(`{"query":"add("}`)}},
						protocol.ToolCall{Function: protocol.CallFunction{Name: "repository_read", Arguments: json.RawMessage(`{"path":"helper.py","start":1,"end":0}`)}},
					)
					answer, _ := json.Marshal(protocol.Report{Summary: "Inspected five files and callers", Limitations: "Fixture judgments", Findings: findings})
					provider.answers = []string{string(answer)}
				}
			}
			session := Session{
				Launcher: launcher, Manifest: manifest, Repository: reader,
				Profiles: map[string]Profile{"review": {Provider: provider, Model: "fixture"}},
				Job: protocol.Job{Number: 42, Title: "Fix addition", AllowedCapabilities: grants,
					ChangedFiles: []protocol.ChangedFile{{Path: "add.py", Status: "modified"}},
					TrustedInstructions: []protocol.Instruction{
						{Scope: ".", Content: "root-guidance-marker"},
						{Scope: "other", Content: "unrelated-guidance-marker"},
					}},
			}
			if tc.broad {
				session.Job.ChangedFiles = nil
				for i := 0; i < 5; i++ {
					path := "file" + string(rune('0'+i)) + ".py"
					session.Job.ChangedFiles = append(session.Job.ChangedFiles, protocol.ChangedFile{Path: path, Status: "modified"})
					if err := os.WriteFile(filepath.Join(checkout, path), []byte(strings.Repeat("return a - b\n", 220)), 0600); err != nil {
						t.Fatal(err)
					}
				}
				if err := os.WriteFile(filepath.Join(checkout, "helper.py"), []byte("add(1, 2)\n"), 0600); err != nil {
					t.Fatal(err)
				}
			}
			if tc.tests {
				session.Job.TestProfiles = []string{"unit"}
				session.Tests = testExecFunc(func(_ context.Context, profile string) (protocol.TestResult, error) {
					code := 1
					return protocol.TestResult{Profile: profile, ExitCode: &code, Output: "TestAdd FAILED"}, nil
				})
			}
			ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
			defer cancel()
			report, err := session.Run(ctx)
			if tc.wantFailure {
				if err == nil {
					t.Fatalf("failed session returned a successful report: %+v", report)
				}
			} else {
				if err != nil {
					t.Fatal(err)
				}
				if report.Findings == nil || len(report.Findings) != tc.wantFindings {
					t.Fatalf("unexpected findings: %+v", report)
				}
				if tc.broad && !strings.Contains(report.Limitations, "5 of 5") {
					t.Fatal("whole-PR coverage lost")
				}
				if tc.truncated && !strings.Contains(report.Limitations, "truncated") {
					t.Fatal("lost truncation")
				}
				if tc.agent != "code-review" && !strings.Contains(report.Limitations, "no defect analysis") && !strings.Contains(report.Limitations, "Metadata only") {
					t.Fatal("lost starter limitations")
				}
			}
			if provider.chats > 0 {
				if provider.unloads != 1 {
					t.Fatalf("model was not unloaded: %d", provider.unloads)
				}
				if !strings.Contains(provider.messages[0].Content, "root-guidance-marker") || strings.Contains(provider.messages[0].Content, "unrelated-guidance-marker") {
					t.Fatal("guidance scope was lost")
				}
			}
			if tc.tests && (!strings.Contains(report.Limitations, "head only")) {
				t.Fatal("head-only test limitation was lost")
			}
			if tc.tests && tc.agent == "code-review" {
				evidence, _ := json.Marshal(provider.messages)
				if !strings.Contains(string(evidence), "TestAdd FAILED") {
					t.Fatal("test evidence was lost")
				}
			}
			if tc.agent == "test-summary" && tc.tests && !strings.Contains(report.Summary, "unit: FAILED") {
				t.Fatalf("observed failure missing from test summary: %+v", report)
			}
		})
	}
}

// Run the model-free test summarizer through the actual agent and test sandboxes.
func TestOfficialAgentsTestSummaryRunsTests(t *testing.T) {
	root, agentImage, testImage := os.Getenv("GIAD_OFFICIAL_AGENTS_ROOT"), os.Getenv("GIAD_OFFICIAL_IMAGE"), os.Getenv("GIAD_OFFICIAL_TEST_IMAGE")
	if agentImage == "" || testImage == "" {
		t.Skip("make sandbox-smoke runs real agent and test containers")
	}
	manifest, err := LoadManifest(filepath.Join(root, "agents/test-summary/agent.manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	grants, err := Grants(manifest, []string{"repository.instructions", "tests.run"})
	if err != nil {
		t.Fatal(err)
	}
	checkout := t.TempDir()
	for name, source := range map[string]string{
		"add.py":      "def add(a, b):\n    return a - b\n",
		"test_add.py": "import unittest\nfrom add import add\nclass TestAdd(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n",
	} {
		if err := os.WriteFile(filepath.Join(checkout, name), []byte(source), 0600); err != nil {
			t.Fatal(err)
		}
	}
	reader, err := tools.Open(checkout, "")
	if err != nil {
		t.Fatal(err)
	}
	defer reader.Close()
	runner := &sandbox.TestRunner{Checkout: checkout, Profiles: map[string]sandbox.TestProfile{
		"unit":  {Image: testImage, Command: "/usr/local/bin/python3", Args: []string{"-m", "unittest", "discover"}, TimeoutSeconds: 30},
		"smoke": {Image: testImage, Command: "/usr/local/bin/python3", Args: []string{"-c", "from add import add; assert add(0, 0) == 0"}, TimeoutSeconds: 30},
	}}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()
	report, err := (Session{Launcher: sandbox.DockerLauncher{Image: agentImage}, Manifest: manifest, Repository: reader, Tests: runner,
		Job: protocol.Job{AllowedCapabilities: grants, TestProfiles: []string{"unit", "smoke"}},
	}).Run(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(runner.Results) != 2 || runner.Results[0].ExitCode == nil || *runner.Results[0].ExitCode != 1 || runner.Results[1].ExitCode == nil || *runner.Results[1].ExitCode != 0 {
		t.Fatalf("observed results missing: %+v", runner.Results)
	}
	if !strings.Contains(runner.Results[0].Output, "test_add") || !strings.Contains(report.Summary, "unit: FAILED") || !strings.Contains(report.Summary, "smoke: PASSED") || len(report.Findings) != 0 {
		t.Fatalf("incorrect test summary: report=%+v results=%+v", report, runner.Results)
	}
}
