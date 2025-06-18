"use client"

import { useState, useEffect } from "react"

export default function JiraOptimizedPage() {
  const [brdContent, setBrdContent] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedStories, setGeneratedStories] = useState<any[]>([])
  const [message, setMessage] = useState("🚀 PO Assist loaded in Jira!")
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    // IMMEDIATE load to prevent Jira timeout
    setIsReady(true)

    // Jira-specific iframe setup
    const setupJiraIframe = () => {
      // Signal to Jira that we're ready
      if (window.parent !== window) {
        try {
          // Send ready signal
          window.parent.postMessage(
            {
              type: "jira-addon-ready",
              source: "po-assist",
              timestamp: Date.now(),
            },
            "*",
          )

          // Auto-resize function
          const sendHeight = () => {
            const height = Math.max(document.documentElement.scrollHeight, 300)
            window.parent.postMessage(
              {
                type: "jira-resize",
                height: height,
                source: "po-assist",
              },
              "*",
            )
          }

          // Send initial height quickly
          setTimeout(sendHeight, 10)
          setTimeout(sendHeight, 100)
          setTimeout(sendHeight, 500)

          // Monitor changes
          const observer = new MutationObserver(() => {
            setTimeout(sendHeight, 50)
          })
          observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
          })

          // Cleanup
          return () => observer.disconnect()
        } catch (e) {
          console.log("Jira iframe setup complete")
        }
      }
    }

    setupJiraIframe()
  }, [])

  // Trigger resize when stories change
  useEffect(() => {
    if (window.parent !== window) {
      setTimeout(() => {
        const height = Math.max(document.documentElement.scrollHeight, 300)
        window.parent.postMessage(
          {
            type: "jira-resize",
            height: height,
            source: "po-assist",
          },
          "*",
        )
      }, 100)
    }
  }, [generatedStories])

  const generateStories = async () => {
    if (!brdContent.trim()) {
      setMessage("❌ Please enter BRD content")
      return
    }

    setIsGenerating(true)
    setMessage("⏳ Generating stories with AI...")

    try {
      const response = await fetch("/api/generate-stories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brdContent,
          projectName: "Jira Project",
        }),
      })

      if (!response.ok) throw new Error("Generation failed")

      const data = await response.json()
      setGeneratedStories(data.stories)
      setMessage(`✅ Generated ${data.stories.length} stories successfully!`)
    } catch (error) {
      setMessage("❌ Failed to generate stories. Please try again.")
      console.error("Generation error:", error)
    } finally {
      setIsGenerating(false)
    }
  }

  const publishToJira = async () => {
    if (generatedStories.length === 0) return

    setMessage("⏳ Publishing to your Jira project...")

    try {
      const response = await fetch("/api/publish-to-jira", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stories: generatedStories,
          projectKey: "TEST", // Will use your default project
        }),
      })

      if (!response.ok) throw new Error("Publishing failed")

      const data = await response.json()
      setMessage(`✅ Published ${data.publishedCount} stories to Jira! Check your backlog.`)

      // Notify Jira to refresh
      if (window.parent !== window) {
        window.parent.postMessage(
          {
            type: "jira-refresh",
            source: "po-assist",
          },
          "*",
        )
      }
    } catch (error) {
      setMessage("❌ Failed to publish to Jira. Check your connection in Settings.")
      console.error("Publishing error:", error)
    }
  }

  // Fast loading state
  if (!isReady) {
    return (
      <div
        style={{
          padding: "20px",
          textAlign: "center",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          backgroundColor: "white",
        }}
      >
        <div>Loading...</div>
      </div>
    )
  }

  return (
    <div
      style={{
        padding: "12px",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        backgroundColor: "white",
        minHeight: "300px",
        fontSize: "14px",
        lineHeight: "1.4",
      }}
    >
      {/* Compact Header for Jira */}
      <div
        style={{
          background: "linear-gradient(90deg, #0052cc 0%, #0065ff 100%)",
          color: "white",
          padding: "8px 12px",
          borderRadius: "4px",
          marginBottom: "12px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div style={{ fontSize: "16px", fontWeight: "600", margin: 0 }}>🚀 PO Assist</div>
          <div style={{ fontSize: "11px", opacity: 0.9, margin: 0 }}>AI Story Generator</div>
        </div>
        <div
          style={{
            backgroundColor: "rgba(255,255,255,0.2)",
            padding: "2px 6px",
            borderRadius: "3px",
            fontSize: "10px",
            fontWeight: "500",
          }}
        >
          ✓ ACTIVE
        </div>
      </div>

      {/* Status Message */}
      <div
        style={{
          padding: "6px 10px",
          marginBottom: "12px",
          backgroundColor: message.includes("❌") ? "#ffebee" : message.includes("⏳") ? "#fff3e0" : "#e8f5e8",
          border: `1px solid ${message.includes("❌") ? "#ffcdd2" : message.includes("⏳") ? "#ffcc02" : "#c8e6c8"}`,
          borderRadius: "3px",
          fontSize: "12px",
          color: message.includes("❌") ? "#c62828" : message.includes("⏳") ? "#ef6c00" : "#2e7d32",
        }}
      >
        {message}
      </div>

      {/* BRD Input */}
      <div style={{ marginBottom: "12px" }}>
        <label
          style={{
            display: "block",
            marginBottom: "4px",
            fontWeight: "500",
            fontSize: "12px",
            color: "#172b4d",
          }}
        >
          📋 Business Requirements Document:
        </label>
        <textarea
          value={brdContent}
          onChange={(e) => setBrdContent(e.target.value)}
          placeholder="Paste your BRD content here to generate EPICs and user stories..."
          style={{
            width: "100%",
            height: "80px",
            padding: "6px",
            border: "1px solid #dfe1e6",
            borderRadius: "3px",
            fontSize: "12px",
            fontFamily: "inherit",
            resize: "vertical",
            boxSizing: "border-box",
            outline: "none",
          }}
          onFocus={(e) => {
            e.target.style.borderColor = "#0052cc"
            e.target.style.boxShadow = "0 0 0 2px rgba(0, 82, 204, 0.2)"
          }}
          onBlur={(e) => {
            e.target.style.borderColor = "#dfe1e6"
            e.target.style.boxShadow = "none"
          }}
        />
      </div>

      {/* Action Buttons */}
      <div style={{ marginBottom: "12px", display: "flex", gap: "8px" }}>
        <button
          onClick={generateStories}
          disabled={isGenerating || !brdContent.trim()}
          style={{
            backgroundColor: isGenerating || !brdContent.trim() ? "#f4f5f7" : "#0052cc",
            color: isGenerating || !brdContent.trim() ? "#6b778c" : "white",
            border: "none",
            padding: "8px 12px",
            borderRadius: "3px",
            cursor: isGenerating || !brdContent.trim() ? "not-allowed" : "pointer",
            fontSize: "12px",
            fontWeight: "500",
            flex: 1,
            transition: "background-color 0.2s",
          }}
        >
          {isGenerating ? "⏳ Generating..." : "✨ Generate Stories"}
        </button>

        {generatedStories.length > 0 && (
          <button
            onClick={publishToJira}
            style={{
              backgroundColor: "#00875a",
              color: "white",
              border: "none",
              padding: "8px 12px",
              borderRadius: "3px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: "500",
              flex: 1,
              transition: "background-color 0.2s",
            }}
            onMouseOver={(e) => {
              e.target.style.backgroundColor = "#006644"
            }}
            onMouseOut={(e) => {
              e.target.style.backgroundColor = "#00875a"
            }}
          >
            📤 Publish to Jira
          </button>
        )}
      </div>

      {/* Generated Stories */}
      {generatedStories.length > 0 && (
        <div>
          <div
            style={{
              fontSize: "13px",
              fontWeight: "600",
              color: "#172b4d",
              marginBottom: "8px",
              paddingBottom: "4px",
              borderBottom: "2px solid #0052cc",
            }}
          >
            📝 Generated Stories ({generatedStories.length}):
          </div>
          <div style={{ maxHeight: "200px", overflowY: "auto" }}>
            {generatedStories.slice(0, 8).map((story, index) => (
              <div
                key={index}
                style={{
                  backgroundColor: "#f4f5f7",
                  border: "1px solid #dfe1e6",
                  borderRadius: "3px",
                  padding: "6px",
                  marginBottom: "4px",
                  fontSize: "11px",
                }}
              >
                <div style={{ marginBottom: "3px", display: "flex", gap: "4px" }}>
                  <span
                    style={{
                      backgroundColor: story.type === "epic" ? "#0052cc" : "#6b778c",
                      color: "white",
                      padding: "1px 4px",
                      borderRadius: "2px",
                      fontSize: "9px",
                      fontWeight: "600",
                    }}
                  >
                    {story.type.toUpperCase()}
                  </span>
                  <span
                    style={{
                      backgroundColor: "#dfe1e6",
                      color: "#42526e",
                      padding: "1px 4px",
                      borderRadius: "2px",
                      fontSize: "9px",
                    }}
                  >
                    {story.priority}
                  </span>
                </div>
                <div style={{ fontWeight: "500", marginBottom: "2px", color: "#172b4d" }}>{story.title}</div>
                <div style={{ color: "#6b778c", lineHeight: "1.3" }}>
                  {story.description?.substring(0, 80)}
                  {story.description?.length > 80 ? "..." : ""}
                </div>
              </div>
            ))}
            {generatedStories.length > 8 && (
              <div style={{ textAlign: "center", color: "#6b778c", fontSize: "10px", padding: "4px" }}>
                ... and {generatedStories.length - 8} more stories
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
