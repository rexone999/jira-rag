"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, MessageSquare, FileText, Zap, CheckCircle, ExternalLink, Settings } from "lucide-react"
import { ChatInterface } from "@/components/chat-interface"
import { UserStoryManager } from "@/components/user-story-manager"
import { BRDUploader } from "@/components/brd-uploader"
import { JiraTestPanel } from "@/components/jira-test-panel"

export default function MainPage() {
  const [activeTab, setActiveTab] = useState("upload")
  const [generatedStories, setGeneratedStories] = useState([])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-600 p-2 rounded-lg">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">PO Assist</h1>
                <p className="text-sm text-gray-500">AI-Powered Story Generation</p>
              </div>
            </div>
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <CheckCircle className="h-3 w-3 mr-1" />
              Jira Connected
            </Badge>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Transform BRDs into Actionable Stories</h2>
          <p className="text-lg text-gray-600">
            Upload your Business Requirements Document and let AI generate EPICs and user stories, then publish them
            directly to your Jira backlog.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5 lg:w-3/5">
            <TabsTrigger value="upload" className="flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>Upload BRD</span>
            </TabsTrigger>
            <TabsTrigger value="stories" className="flex items-center space-x-2">
              <FileText className="h-4 w-4" />
              <span>Stories</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className="flex items-center space-x-2">
              <MessageSquare className="h-4 w-4" />
              <span>Chat</span>
            </TabsTrigger>
            <TabsTrigger value="jira" className="flex items-center space-x-2">
              <ExternalLink className="h-4 w-4" />
              <span>Jira</span>
            </TabsTrigger>
            <TabsTrigger value="test" className="flex items-center space-x-2">
              <Settings className="h-4 w-4" />
              <span>Test</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <BRDUploader onStoriesGenerated={setGeneratedStories} />
          </TabsContent>

          <TabsContent value="stories" className="space-y-6">
            <UserStoryManager stories={generatedStories} />
          </TabsContent>

          <TabsContent value="chat" className="space-y-6">
            <ChatInterface onStoriesGenerated={setGeneratedStories} />
          </TabsContent>

          <TabsContent value="jira" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <ExternalLink className="h-5 w-5" />
                  <span>Jira Integration</span>
                </CardTitle>
                <CardDescription>Manage your Jira connection and view published stories</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg border border-green-200">
                    <div>
                      <p className="font-medium text-green-800">Connected to Jira</p>
                      <p className="text-sm text-green-600">projectmajorvd25.atlassian.net</p>
                    </div>
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  </div>
                  <Button
                    onClick={() => window.open("https://projectmajorvd25.atlassian.net", "_blank")}
                    className="w-full"
                  >
                    Open Jira Dashboard
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="test" className="space-y-6">
            <JiraTestPanel />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
