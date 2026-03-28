import React, { useState, useCallback, useRef, useEffect, memo } from 'react'
import ReactFlow, {
  addEdge,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Panel,
} from 'reactflow'
import 'reactflow/dist/style.css'

import TriggerNode from './nodes/TriggerNode'
import AgentNode from './nodes/AgentNode'
import HTTPNode from './nodes/HTTPNode'
import ConditionNode from './nodes/ConditionNode'
import TransformNode from './nodes/TransformNode'
import EmailNode from './nodes/EmailNode'
import FileSaveNode from './nodes/FileSaveNode'
import FileReadNode from './nodes/FileReadNode'
import NotificationNode from './nodes/NotificationNode'
import ChatbotTriggerNode from './nodes/ChatbotTriggerNode'
import LoopNode from './nodes/LoopNode'
import SwitchNode from './nodes/SwitchNode'
import ForkNode from './nodes/ForkNode'
import JoinNode from './nodes/JoinNode'
import ErrorHandlerNode from './nodes/ErrorHandlerNode'
import ApprovalNode from './nodes/ApprovalNode'
import DelayNode from './nodes/DelayNode'
import ForEachNode from './nodes/ForEachNode'
import SubWorkflowNode from './nodes/SubWorkflowNode'
import WebhookResponseNode from './nodes/WebhookResponseNode'
import CommentNode from './nodes/CommentNode'
import GroupNode from './nodes/GroupNode'
import DatabaseNode from './nodes/DatabaseNode'
import CloudStorageNode from './nodes/CloudStorageNode'
import GoogleSheetsNode from './nodes/GoogleSheetsNode'
import DataTransformNode from './nodes/DataTransformNode'
import PythonCodeNode from './nodes/PythonCodeNode'
import DirectoryPicker from '../common/DirectoryPicker'
import FilePicker from '../common/FilePicker'
import AgentHierarchyConfig, { 
  SYSTEM_AGENTS_FOR_HIERARCHY,
  convertFlatToHierarchy,
  convertHierarchyToFlat
} from './AgentHierarchyConfig'
import { useToast } from '../common/ToastProvider'
import { useAuth } from '../../contexts/AuthContext'
import { workflowsApi, llmConfigsApi, integrationsApi } from '../../services/api'
import './WorkflowEditor.css'

const nodeTypes = {
  trigger: TriggerNode,
  chatbot_trigger: ChatbotTriggerNode,
  agent: AgentNode,
  http: HTTPNode,
  condition: ConditionNode,
  transform: TransformNode,
  email: EmailNode,
  file_save: FileSaveNode,
  file_read: FileReadNode,
  notification: NotificationNode,
  loop: LoopNode,
  switch: SwitchNode,
  fork: ForkNode,
  join: JoinNode,
  error_handler: ErrorHandlerNode,
  approval: ApprovalNode,
  delay: DelayNode,
  foreach: ForEachNode,
  sub_workflow: SubWorkflowNode,
  webhook_response: WebhookResponseNode,
  comment: CommentNode,
  group: GroupNode,
  database: DatabaseNode,
  cloud_storage: CloudStorageNode,
  google_sheets: GoogleSheetsNode,
  data_transform: DataTransformNode,
  python_code: PythonCodeNode,
}

const NodeConfigForm = memo(function NodeConfigForm({ 
  node, 
  onChange,
  llmConfigs = [],
  emailConfigs = [],
  slackConfigs = [],
  teamsConfigs = [],
}) {
  const { type, data } = node
  const [localConfig, setLocalConfig] = useState(data.config || {})
  const [localLabel, setLocalLabel] = useState(data.label || '')

  useEffect(() => {
    setLocalConfig(data.config || {})
    setLocalLabel(data.label || '')
  }, [node.id])

  const handleConfigChange = (field, value) => {
    const newConfig = { ...localConfig, [field]: value }
    setLocalConfig(newConfig)
    onChange({ config: newConfig })
  }

  const handleLabelChange = (value) => {
    setLocalLabel(value)
    onChange({ label: value })
  }

  return (
    <div className="config-form">
      <div className="form-group">
        <label>Label</label>
        <input
          type="text"
          value={localLabel}
          onChange={(e) => handleLabelChange(e.target.value)}
        />
      </div>

      {type === 'trigger' && data.subType === 'schedule' && (
        <div className="form-group">
          <label>Cron Expression</label>
          <input
            type="text"
            value={localConfig.cron || ''}
            onChange={(e) => handleConfigChange('cron', e.target.value)}
            placeholder="0 9 * * *"
          />
          <span className="form-hint">e.g., "0 9 * * *" for daily at 9 AM</span>
        </div>
      )}

      {type === 'trigger' && data.subType === 'webhook' && (
        <div className="form-group">
          <label>Webhook URL</label>
          <input
            type="text"
            value={`/api/webhooks/${node.id}`}
            disabled
          />
          <span className="form-hint">This URL will be generated after saving</span>
        </div>
      )}

      {type === 'chatbot_trigger' && (
        <>
          <div className="form-group">
            <label>Bot Name</label>
            <input
              type="text"
              value={localConfig.bot_name || ''}
              onChange={(e) => handleConfigChange('bot_name', e.target.value)}
              placeholder="JarvisX Assistant"
            />
            <span className="form-hint">Display name shown in the chat interface</span>
          </div>
          <div className="form-group">
            <label>Chat Mode</label>
            <select
              value={localConfig.chat_mode || 'both'}
              onChange={(e) => handleConfigChange('chat_mode', e.target.value)}
            >
              <option value="text">Text Only</option>
              <option value="voice">Voice Only</option>
              <option value="both">Text + Voice</option>
            </select>
            <span className="form-hint">Input methods available to users</span>
          </div>
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={localConfig.allow_file_upload !== false}
                onChange={(e) => handleConfigChange('allow_file_upload', e.target.checked)}
              />
              <span>Allow file uploads</span>
            </label>
            <span className="form-hint">Enable users to attach images, documents, audio, and video</span>
          </div>
          <div className="form-group agent-hierarchy-section">
            <label>Agent Hierarchy</label>
            <span className="form-hint">Configure which agents the orchestrator can delegate to, and their sub-agents. Expand agents to configure nested hierarchies.</span>
            <AgentHierarchyConfig
              agentCodes={SYSTEM_AGENTS_FOR_HIERARCHY}
              config={localConfig.agent_hierarchy || convertFlatToHierarchy(localConfig.connected_agents)}
              onChange={(newHierarchy) => {
                handleConfigChange('agent_hierarchy', newHierarchy)
                handleConfigChange('connected_agents', convertHierarchyToFlat(newHierarchy))
              }}
              depth={0}
              maxDepth={10}
            />
          </div>
          {localConfig.chatbot_url && (
            <div className="form-group">
              <label>Chatbot URL</label>
              <div className="url-display">
                <input
                  type="text"
                  value={localConfig.chatbot_url}
                  readOnly
                />
                <button
                  type="button"
                  className="btn-copy"
                  onClick={() => {
                    navigator.clipboard.writeText(localConfig.chatbot_url)
                  }}
                >
                  Copy
                </button>
              </div>
              <span className="form-hint">Share this URL with users to access the chatbot</span>
            </div>
          )}
        </>
      )}

      {type === 'agent' && (
        <>
          <div className="form-group">
            <label>Agent</label>
            <select
              value={localConfig.agent || ''}
              onChange={(e) => handleConfigChange('agent', e.target.value)}
            >
              <option value="">Select an agent</option>
              <option value="orchestrator">Orchestrator</option>
              <option value="developer">Developer</option>
              <option value="researcher">Researcher</option>
              <option value="browser">Browser</option>
              <option value="knowledge">Knowledge</option>
            </select>
          </div>
          <div className="form-group">
            <label>Prompt</label>
            <textarea
              value={localConfig.prompt || ''}
              onChange={(e) => handleConfigChange('prompt', e.target.value)}
              placeholder="Enter the prompt for the agent..."
              rows={4}
            />
            <span className="form-hint">Use {'{{input}}'} to reference previous node output</span>
          </div>
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={localConfig.include_file_content !== false}
                onChange={(e) => handleConfigChange('include_file_content', e.target.checked)}
              />
              <span>Include file content (multimodal)</span>
            </label>
            <span className="form-hint">Send images, PDFs, audio, and video files from connected FileRead nodes to the agent for analysis</span>
          </div>
          {llmConfigs.length > 0 && (
            <div className="form-group">
              <label>LLM Configuration</label>
              <select
                value={localConfig.llm_config_id || ''}
                onChange={(e) => handleConfigChange('llm_config_id', e.target.value || null)}
              >
                <option value="">Use Organization Default</option>
                {llmConfigs.map(config => (
                  <option key={config.id} value={config.id}>
                    {config.name} {config.is_default ? '(Default)' : ''} - {config.model_name}
                  </option>
                ))}
              </select>
              <span className="form-hint">Select specific LLM configuration or use organization default</span>
            </div>
          )}
        </>
      )}

      {type === 'http' && (
        <>
          <div className="form-group">
            <label>Method</label>
            <select
              value={localConfig.method || 'GET'}
              onChange={(e) => handleConfigChange('method', e.target.value)}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>
          <div className="form-group">
            <label>URL</label>
            <input
              type="text"
              value={localConfig.url || ''}
              onChange={(e) => handleConfigChange('url', e.target.value)}
              placeholder="https://api.example.com/endpoint"
            />
          </div>
          <div className="form-group">
            <label>Headers (JSON)</label>
            <textarea
              value={localConfig.headers || '{}'}
              onChange={(e) => handleConfigChange('headers', e.target.value)}
              placeholder='{"Content-Type": "application/json"}'
              rows={3}
            />
          </div>
          <div className="form-group">
            <label>Body (JSON)</label>
            <textarea
              value={localConfig.body || ''}
              onChange={(e) => handleConfigChange('body', e.target.value)}
              placeholder='{"key": "value"}'
              rows={4}
            />
          </div>
        </>
      )}

      {type === 'condition' && (
        <>
          <div className="form-group">
            <label>Condition</label>
            <input
              type="text"
              value={localConfig.condition || ''}
              onChange={(e) => handleConfigChange('condition', e.target.value)}
              placeholder="{{input.status}} === 'success'"
            />
            <span className="form-hint">JavaScript expression that evaluates to true/false</span>
          </div>
        </>
      )}

      {type === 'loop' && (
        <>
          <div className="form-group">
            <label>Max Iterations</label>
            <input
              type="number"
              min="1"
              max="100"
              value={localConfig.max_iterations || 5}
              onChange={(e) => handleConfigChange('max_iterations', parseInt(e.target.value, 10))}
            />
          </div>
          <div className="form-group">
            <label>Break Condition (optional)</label>
            <input
              type="text"
              value={localConfig.break_condition || ''}
              onChange={(e) => handleConfigChange('break_condition', e.target.value)}
              placeholder="input.status === 'done'"
            />
            <span className="form-hint">Loop exits when this evaluates to true. Access loop.index and loop.iteration.</span>
          </div>
        </>
      )}

      {type === 'switch' && (
        <>
          <div className="form-group">
            <label>Switch Expression</label>
            <input
              type="text"
              value={localConfig.expression || ''}
              onChange={(e) => handleConfigChange('expression', e.target.value)}
              placeholder="input.category"
            />
            <span className="form-hint">Expression whose value determines which branch to take</span>
          </div>
          <div className="form-group">
            <label>Cases (JSON Array)</label>
            <textarea
              value={localConfig.cases ? JSON.stringify(localConfig.cases, null, 2) : '[{"label": "case1", "value": "A"}]'}
              onChange={(e) => {
                try { handleConfigChange('cases', JSON.parse(e.target.value)) } catch {}
              }}
              placeholder='[{"label": "case1", "value": "A"}, {"label": "case2", "value": "B"}]'
              rows={4}
            />
            <span className="form-hint">Each case needs "label" (handle ID) and "value" to match. Always has a "default" branch.</span>
          </div>
        </>
      )}

      {type === 'fork' && (
        <div className="form-group">
          <label>Number of Branches</label>
          <input
            type="number"
            min="2"
            max="10"
            value={localConfig.branches || 2}
            onChange={(e) => handleConfigChange('branches', parseInt(e.target.value, 10))}
          />
          <span className="form-hint">Splits execution into parallel branches</span>
        </div>
      )}

      {type === 'error_handler' && (
        <div className="form-group">
          <span className="form-hint">
            Connect the "✓" handle to nodes you want to protect.
            If any fails, execution routes to the "✗" handle instead of failing the workflow.
          </span>
        </div>
      )}

      {type === 'approval' && (
        <>
          <div className="form-group">
            <label>Approval Message</label>
            <textarea
              value={localConfig.message || ''}
              onChange={(e) => handleConfigChange('message', e.target.value)}
              placeholder="Please review and approve this workflow step"
              rows={3}
            />
          </div>
          <div className="form-group">
            <label>Approvers (comma-separated)</label>
            <input
              type="text"
              value={(localConfig.approvers || []).join(', ')}
              onChange={(e) => handleConfigChange('approvers', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
              placeholder="admin@example.com, manager@example.com"
            />
          </div>
        </>
      )}

      {type === 'delay' && (
        <>
          <div className="form-group">
            <label>Delay (seconds)</label>
            <input
              type="number"
              min="0"
              max="3600"
              value={localConfig.delay_seconds || 0}
              onChange={(e) => handleConfigChange('delay_seconds', parseInt(e.target.value, 10))}
            />
            <span className="form-hint">Max 3600 seconds (1 hour)</span>
          </div>
        </>
      )}

      {type === 'foreach' && (
        <div className="form-group">
          <label>Array Field</label>
          <input
            type="text"
            value={localConfig.array_field || 'items'}
            onChange={(e) => handleConfigChange('array_field', e.target.value)}
            placeholder="items"
          />
          <span className="form-hint">Field name in input data containing the array to iterate over. Each iteration gets foreach.index, foreach.item.</span>
        </div>
      )}

      {type === 'sub_workflow' && (
        <div className="form-group">
          <label>Sub-Workflow ID</label>
          <input
            type="text"
            value={localConfig.workflow_id || ''}
            onChange={(e) => handleConfigChange('workflow_id', e.target.value)}
            placeholder="Enter workflow ID"
          />
          <span className="form-hint">ID of the workflow to execute as a sub-workflow</span>
        </div>
      )}

      {type === 'webhook_response' && (
        <>
          <div className="form-group">
            <label>Status Code</label>
            <input
              type="number"
              value={localConfig.status_code || 200}
              onChange={(e) => handleConfigChange('status_code', parseInt(e.target.value, 10))}
            />
          </div>
          <div className="form-group">
            <label>Response Body</label>
            <textarea
              value={localConfig.body || ''}
              onChange={(e) => handleConfigChange('body', e.target.value)}
              placeholder='{"status": "ok", "result": "{{input.response}}"}'
              rows={4}
            />
            <span className="form-hint">Response sent back to webhook caller. Supports variable interpolation.</span>
          </div>
        </>
      )}

      {type === 'database' && (
        <>
          <div className="form-group">
            <label>Operation</label>
            <select value={localConfig.operation || 'query'} onChange={(e) => handleConfigChange('operation', e.target.value)}>
              <option value="query">Query (SELECT)</option>
              <option value="execute">Execute (INSERT/UPDATE/DELETE)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Connection String</label>
            <input type="text" value={localConfig.connection_string || ''} onChange={(e) => handleConfigChange('connection_string', e.target.value)} placeholder="postgresql://user:pass@host:5432/db" />
          </div>
          <div className="form-group">
            <label>SQL Query</label>
            <textarea value={localConfig.query || ''} onChange={(e) => handleConfigChange('query', e.target.value)} placeholder="SELECT * FROM users WHERE id = '{{input.user_id}}'" rows={4} />
            <span className="form-hint">Supports variable interpolation</span>
          </div>
        </>
      )}

      {type === 'cloud_storage' && (
        <>
          <div className="form-group">
            <label>Provider</label>
            <select value={localConfig.provider || 's3'} onChange={(e) => handleConfigChange('provider', e.target.value)}>
              <option value="s3">AWS S3</option>
            </select>
          </div>
          <div className="form-group">
            <label>Operation</label>
            <select value={localConfig.operation || 'download'} onChange={(e) => handleConfigChange('operation', e.target.value)}>
              <option value="download">Download</option>
              <option value="upload">Upload</option>
              <option value="list">List Files</option>
            </select>
          </div>
          <div className="form-group">
            <label>Bucket</label>
            <input type="text" value={localConfig.bucket || ''} onChange={(e) => handleConfigChange('bucket', e.target.value)} placeholder="my-bucket" />
          </div>
          <div className="form-group">
            <label>Key / Path</label>
            <input type="text" value={localConfig.key || ''} onChange={(e) => handleConfigChange('key', e.target.value)} placeholder="folder/file.json" />
          </div>
          <div className="form-group">
            <label>Access Key</label>
            <input type="password" value={localConfig.access_key || ''} onChange={(e) => handleConfigChange('access_key', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Secret Key</label>
            <input type="password" value={localConfig.secret_key || ''} onChange={(e) => handleConfigChange('secret_key', e.target.value)} />
          </div>
        </>
      )}

      {type === 'google_sheets' && (
        <>
          <div className="form-group">
            <label>Operation</label>
            <select value={localConfig.operation || 'read'} onChange={(e) => handleConfigChange('operation', e.target.value)}>
              <option value="read">Read</option>
              <option value="append">Append Rows</option>
            </select>
          </div>
          <div className="form-group">
            <label>Spreadsheet ID</label>
            <input type="text" value={localConfig.spreadsheet_id || ''} onChange={(e) => handleConfigChange('spreadsheet_id', e.target.value)} placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms" />
          </div>
          <div className="form-group">
            <label>Range</label>
            <input type="text" value={localConfig.range || 'Sheet1!A1:Z1000'} onChange={(e) => handleConfigChange('range', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Service Account JSON</label>
            <textarea value={localConfig.credentials_json || ''} onChange={(e) => handleConfigChange('credentials_json', e.target.value)} placeholder="Paste service account JSON" rows={4} />
          </div>
        </>
      )}

      {type === 'data_transform' && (
        <>
          <div className="form-group">
            <label>Operation</label>
            <select value={localConfig.operation || 'parse_json'} onChange={(e) => handleConfigChange('operation', e.target.value)}>
              <option value="parse_json">Parse JSON</option>
              <option value="parse_csv">Parse CSV</option>
              <option value="to_csv">Convert to CSV</option>
              <option value="to_json">Convert to JSON</option>
              <option value="filter">Filter Rows</option>
              <option value="aggregate">Aggregate</option>
              <option value="pick_fields">Pick Fields</option>
            </select>
          </div>
          {localConfig.operation === 'filter' && (
            <>
              <div className="form-group">
                <label>Field</label>
                <input type="text" value={localConfig.field || ''} onChange={(e) => handleConfigChange('field', e.target.value)} placeholder="status" />
              </div>
              <div className="form-group">
                <label>Value</label>
                <input type="text" value={localConfig.value || ''} onChange={(e) => handleConfigChange('value', e.target.value)} placeholder="active" />
              </div>
            </>
          )}
          {localConfig.operation === 'aggregate' && (
            <>
              <div className="form-group">
                <label>Field</label>
                <input type="text" value={localConfig.field || ''} onChange={(e) => handleConfigChange('field', e.target.value)} placeholder="amount" />
              </div>
              <div className="form-group">
                <label>Aggregation</label>
                <select value={localConfig.agg_type || 'sum'} onChange={(e) => handleConfigChange('agg_type', e.target.value)}>
                  <option value="count">Count</option>
                  <option value="sum">Sum</option>
                  <option value="avg">Average</option>
                  <option value="min">Min</option>
                  <option value="max">Max</option>
                </select>
              </div>
            </>
          )}
        </>
      )}

      {type === 'python_code' && (
        <div className="form-group">
          <label>Python Code</label>
          <textarea value={localConfig.code || ''} onChange={(e) => handleConfigChange('code', e.target.value)} placeholder="# Access input data via 'input' variable\n# Set 'result' to return output\nresult = {'processed': len(input.get('items', []))}" rows={8} />
          <span className="form-hint">Access input data via 'input'. Set 'result' variable for output. Sandboxed execution.</span>
        </div>
      )}

      {type === 'comment' && (
        <div className="form-group">
          <label>Comment Text</label>
          <textarea
            value={localConfig.text || ''}
            onChange={(e) => handleConfigChange('text', e.target.value)}
            placeholder="Add a note about this part of the workflow..."
            rows={4}
          />
        </div>
      )}

      {type === 'transform' && (
        <div className="form-group">
          <label>Transform Code</label>
          <textarea
            value={localConfig.code || ''}
            onChange={(e) => handleConfigChange('code', e.target.value)}
            placeholder="// Transform input data\nreturn { ...input, transformed: true }"
            rows={6}
          />
          <span className="form-hint">JavaScript code. Use 'input' to access previous node output</span>
        </div>
      )}

      {type === 'email' && (
        <>
          {emailConfigs.length > 0 && (
            <div className="form-group">
              <label>Email Configuration</label>
              <select
                value={localConfig.email_config_id || ''}
                onChange={(e) => handleConfigChange('email_config_id', e.target.value || null)}
              >
                <option value="">Use Organization Default</option>
                {emailConfigs.map(config => (
                  <option key={config.id} value={config.id}>
                    {config.name} {config.is_default ? '(Default)' : ''}
                  </option>
                ))}
              </select>
              <span className="form-hint">Select specific SMTP configuration or use organization default</span>
            </div>
          )}
          <div className="form-group">
            <label>To (Email Addresses)</label>
            <input
              type="text"
              value={localConfig.to || ''}
              onChange={(e) => handleConfigChange('to', e.target.value)}
              placeholder="email@example.com, another@example.com"
            />
            <span className="form-hint">Comma-separated emails. Use {'{{input.email}}'} for dynamic values</span>
          </div>
          <div className="form-group">
            <label>Subject</label>
            <input
              type="text"
              value={localConfig.subject || ''}
              onChange={(e) => handleConfigChange('subject', e.target.value)}
              placeholder="Workflow Output: {{input.title}}"
            />
          </div>
          <div className="form-group">
            <label>Body</label>
            <textarea
              value={localConfig.body || ''}
              onChange={(e) => handleConfigChange('body', e.target.value)}
              placeholder="{{input.response}}"
              rows={6}
            />
            <span className="form-hint">Use {'{{input.response}}'} to include agent output</span>
          </div>
          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={localConfig.include_attachment || false}
                onChange={(e) => handleConfigChange('include_attachment', e.target.checked)}
              />
              Include output as attachment
            </label>
          </div>
          {localConfig.include_attachment && (
            <div className="form-group">
              <label>Attachment Format</label>
              <select
                value={localConfig.attachment_format || 'json'}
                onChange={(e) => handleConfigChange('attachment_format', e.target.value)}
              >
                <option value="json">JSON</option>
                <option value="txt">Plain Text</option>
              </select>
            </div>
          )}
        </>
      )}

      {type === 'file_save' && (
        <>
          <div className="form-group">
            <label>Filename</label>
            <input
              type="text"
              value={localConfig.filename || ''}
              onChange={(e) => handleConfigChange('filename', e.target.value)}
              placeholder="report_{{timestamp}}"
            />
            <span className="form-hint">Use {'{{timestamp}}'} or {'{{date}}'} for dynamic names</span>
          </div>
          <div className="form-group">
            <label>Format</label>
            <select
              value={localConfig.format || 'txt'}
              onChange={(e) => handleConfigChange('format', e.target.value)}
            >
              <option value="txt">Plain Text (.txt)</option>
              <option value="json">JSON (.json)</option>
              <option value="md">Markdown (.md)</option>
              <option value="pdf">PDF (.pdf)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Content</label>
            <textarea
              value={localConfig.content || ''}
              onChange={(e) => handleConfigChange('content', e.target.value)}
              placeholder="{{input.response}}"
              rows={4}
            />
            <span className="form-hint">Use {'{{input.response}}'} to save agent output</span>
          </div>
          <div className="form-group">
            <label>Output Directory</label>
            <DirectoryPicker
              value={localConfig.subdirectory || 'workflow_outputs'}
              onChange={(path) => handleConfigChange('subdirectory', path)}
              placeholder="Select output directory"
            />
          </div>
        </>
      )}

      {type === 'file_read' && (
        <>
          <div className="form-group">
            <label>File Path</label>
            <FilePicker
              value={localConfig.file_path || ''}
              onChange={(path) => handleConfigChange('file_path', path)}
              placeholder="Select file to read"
              extensions="txt,json,md,csv,yaml,yml,xml,log,pdf,doc,docx,xls,xlsx,ppt,pptx,jpg,jpeg,png,gif,webp,bmp,tiff,mp3,wav,ogg,flac,aac,m4a,mp4,webm,avi,mov,mkv"
            />
            <span className="form-hint">Supports text, documents, images, audio, and video files</span>
          </div>
          <div className="form-group">
            <label>Parse Format</label>
            <select
              value={localConfig.parse_format || 'auto'}
              onChange={(e) => handleConfigChange('parse_format', e.target.value)}
            >
              <option value="auto">Auto-detect</option>
              <option value="txt">Plain Text</option>
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
              <option value="yaml">YAML</option>
              <option value="md">Markdown</option>
            </select>
            <span className="form-hint">Auto-detect uses file extension. Binary files are base64 encoded.</span>
          </div>
          <div className="form-group">
            <label>Encoding</label>
            <select
              value={localConfig.encoding || 'utf-8'}
              onChange={(e) => handleConfigChange('encoding', e.target.value)}
            >
              <option value="utf-8">UTF-8</option>
              <option value="ascii">ASCII</option>
              <option value="latin-1">Latin-1</option>
              <option value="utf-16">UTF-16</option>
            </select>
            <span className="form-hint">Only applies to text files</span>
          </div>
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={localConfig.extract_text !== false}
                onChange={(e) => handleConfigChange('extract_text', e.target.checked)}
              />
              <span>Extract text from documents</span>
            </label>
            <span className="form-hint">Automatically extract text from PDFs and Word documents</span>
          </div>
        </>
      )}

      {type === 'notification' && (
        <>
          <div className="form-group">
            <label>Platform</label>
            <select
              value={localConfig.platform || 'slack'}
              onChange={(e) => handleConfigChange('platform', e.target.value)}
            >
              <option value="slack">Slack</option>
              <option value="teams">Microsoft Teams</option>
              <option value="discord">Discord</option>
            </select>
          </div>
          {localConfig.platform === 'slack' && slackConfigs.length > 0 && (
            <div className="form-group">
              <label>Slack Configuration</label>
              <select
                value={localConfig.slack_config_id || ''}
                onChange={(e) => handleConfigChange('slack_config_id', e.target.value || null)}
              >
                <option value="">Use Organization Default</option>
                {slackConfigs.map(config => (
                  <option key={config.id} value={config.id}>
                    {config.name} {config.is_default ? '(Default)' : ''}
                  </option>
                ))}
              </select>
              <span className="form-hint">Select specific Slack configuration or use organization default</span>
            </div>
          )}
          {localConfig.platform === 'teams' && teamsConfigs.length > 0 && (
            <div className="form-group">
              <label>Teams Configuration</label>
              <select
                value={localConfig.teams_config_id || ''}
                onChange={(e) => handleConfigChange('teams_config_id', e.target.value || null)}
              >
                <option value="">Use Organization Default</option>
                {teamsConfigs.map(config => (
                  <option key={config.id} value={config.id}>
                    {config.name} {config.is_default ? '(Default)' : ''}
                  </option>
                ))}
              </select>
              <span className="form-hint">Select specific Teams configuration or use organization default</span>
            </div>
          )}
          <div className="form-group">
            <label>Webhook URL (Override)</label>
            <input
              type="text"
              value={localConfig.webhook_url || ''}
              onChange={(e) => handleConfigChange('webhook_url', e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
            />
            <span className="form-hint">Optional. If empty, uses the selected configuration's webhook URL</span>
          </div>
          {localConfig.platform === 'slack' && (
            <div className="form-group">
              <label>Channel (Optional)</label>
              <input
                type="text"
                value={localConfig.channel || ''}
                onChange={(e) => handleConfigChange('channel', e.target.value)}
                placeholder="#general"
              />
            </div>
          )}
          <div className="form-group">
            <label>Message</label>
            <textarea
              value={localConfig.message || ''}
              onChange={(e) => handleConfigChange('message', e.target.value)}
              placeholder="Workflow completed! Result: {{input.response}}"
              rows={4}
            />
            <span className="form-hint">Supports markdown formatting</span>
          </div>
          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={localConfig.include_data || false}
                onChange={(e) => handleConfigChange('include_data', e.target.checked)}
              />
              Include full output data
            </label>
          </div>
        </>
      )}

      {!['trigger', 'chatbot_trigger', 'comment', 'group'].includes(type) && (
        <details className="retry-config-section">
          <summary>Retry Policy</summary>
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={localConfig.retry?.max_retries > 0}
                onChange={(e) => handleConfigChange('retry', e.target.checked
                  ? { max_retries: 3, backoff: 'exponential', initial_delay_ms: 1000 }
                  : { max_retries: 0 }
                )}
              />
              Enable retry on failure
            </label>
          </div>
          {localConfig.retry?.max_retries > 0 && (
            <>
              <div className="form-group">
                <label>Max Retries</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={localConfig.retry?.max_retries || 3}
                  onChange={(e) => handleConfigChange('retry', { ...localConfig.retry, max_retries: parseInt(e.target.value, 10) })}
                />
              </div>
              <div className="form-group">
                <label>Backoff Strategy</label>
                <select
                  value={localConfig.retry?.backoff || 'exponential'}
                  onChange={(e) => handleConfigChange('retry', { ...localConfig.retry, backoff: e.target.value })}
                >
                  <option value="none">None (fixed delay)</option>
                  <option value="linear">Linear</option>
                  <option value="exponential">Exponential</option>
                </select>
              </div>
              <div className="form-group">
                <label>Initial Delay (ms)</label>
                <input
                  type="number"
                  min="100"
                  max="30000"
                  step="100"
                  value={localConfig.retry?.initial_delay_ms || 1000}
                  onChange={(e) => handleConfigChange('retry', { ...localConfig.retry, initial_delay_ms: parseInt(e.target.value, 10) })}
                />
              </div>
            </>
          )}
        </details>
      )}
    </div>
  )
})

const nodeCategories = [
  {
    name: 'Triggers',
    nodes: [
      { type: 'trigger', subType: 'manual', label: 'Manual Trigger', icon: '▶️' },
      { type: 'trigger', subType: 'schedule', label: 'Schedule', icon: '⏰' },
      { type: 'trigger', subType: 'webhook', label: 'Webhook', icon: '🔗' },
      { type: 'chatbot_trigger', subType: 'chatbot', label: 'Chatbot App', icon: '💬' },
    ],
  },
  {
    name: 'Actions',
    nodes: [
      { type: 'agent', label: 'Agent', icon: '🤖' },
      { type: 'http', label: 'HTTP Request', icon: '🌐' },
      { type: 'transform', label: 'Transform', icon: '⚡' },
      { type: 'sub_workflow', label: 'Sub-Workflow', icon: '📋' },
    ],
  },
  {
    name: 'Logic',
    nodes: [
      { type: 'condition', label: 'Condition', icon: '🔀' },
      { type: 'loop', label: 'Loop', icon: '🔁' },
      { type: 'switch', label: 'Switch', icon: '🔀' },
      { type: 'foreach', label: 'For Each', icon: '🔄' },
    ],
  },
  {
    name: 'Flow',
    nodes: [
      { type: 'fork', label: 'Fork', icon: '⑃' },
      { type: 'join', label: 'Join', icon: '⑂' },
      { type: 'delay', label: 'Delay', icon: '⏳' },
      { type: 'error_handler', label: 'Error Handler', icon: '🛡️' },
      { type: 'approval', label: 'Approval', icon: '✋' },
    ],
  },
  {
    name: 'Inputs',
    nodes: [
      { type: 'file_read', label: 'Read File', icon: '📂' },
    ],
  },
  {
    name: 'Outputs',
    nodes: [
      { type: 'email', label: 'Send Email', icon: '📧' },
      { type: 'file_save', label: 'Save File', icon: '💾' },
      { type: 'notification', label: 'Notification', icon: '🔔' },
      { type: 'webhook_response', label: 'Webhook Response', icon: '↩️' },
    ],
  },
  {
    name: 'Integrations',
    nodes: [
      { type: 'database', label: 'Database', icon: '🗄️' },
      { type: 'cloud_storage', label: 'Cloud Storage', icon: '☁️' },
      { type: 'google_sheets', label: 'Google Sheets', icon: '📊' },
      { type: 'data_transform', label: 'Data Transform', icon: '🔧' },
      { type: 'python_code', label: 'Python Code', icon: '🐍' },
    ],
  },
  {
    name: 'Annotations',
    nodes: [
      { type: 'comment', label: 'Comment', icon: '📝' },
      { type: 'group', label: 'Group', icon: '📦' },
    ],
  },
]

let nodeId = 0
const getNodeId = () => `node_${nodeId++}`

function WorkflowEditor({ workflow, onSave, onClose }) {
  const toast = useToast()
  const { user } = useAuth()
  const organizationId = user?.organization_id
  const reactFlowWrapper = useRef(null)
  const [nodes, setNodes, onNodesChange] = useNodesState(workflow?.definition?.nodes || [])
  const [edges, setEdges, onEdgesChange] = useEdgesState(workflow?.definition?.edges || [])
  const [reactFlowInstance, setReactFlowInstance] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [executionStatus, setExecutionStatus] = useState(null)
  const [currentExecutionId, setCurrentExecutionId] = useState(null)
  const [nodeStatuses, setNodeStatuses] = useState({})
  const [isExecuting, setIsExecuting] = useState(false)
  const prevStatusRef = useRef(null)
  
  const [llmConfigs, setLlmConfigs] = useState([])
  const [emailConfigs, setEmailConfigs] = useState([])
  const [slackConfigs, setSlackConfigs] = useState([])
  const [teamsConfigs, setTeamsConfigs] = useState([])

  const historyRef = useRef([])
  const historyIndexRef = useRef(-1)
  const clipboardRef = useRef(null)

  const pushHistory = useCallback(() => {
    const snapshot = { nodes: JSON.parse(JSON.stringify(nodes)), edges: JSON.parse(JSON.stringify(edges)) }
    const newHistory = historyRef.current.slice(0, historyIndexRef.current + 1)
    newHistory.push(snapshot)
    if (newHistory.length > 50) newHistory.shift()
    historyRef.current = newHistory
    historyIndexRef.current = newHistory.length - 1
  }, [nodes, edges])

  const handleUndo = useCallback(() => {
    if (historyIndexRef.current <= 0) return
    historyIndexRef.current -= 1
    const snapshot = historyRef.current[historyIndexRef.current]
    setNodes(snapshot.nodes)
    setEdges(snapshot.edges)
    setHasChanges(true)
  }, [setNodes, setEdges])

  const handleRedo = useCallback(() => {
    if (historyIndexRef.current >= historyRef.current.length - 1) return
    historyIndexRef.current += 1
    const snapshot = historyRef.current[historyIndexRef.current]
    setNodes(snapshot.nodes)
    setEdges(snapshot.edges)
    setHasChanges(true)
  }, [setNodes, setEdges])

  const handleCopyNodes = useCallback(() => {
    const selectedNodes = nodes.filter(n => n.selected)
    if (selectedNodes.length === 0 && selectedNode) {
      clipboardRef.current = { nodes: [selectedNode], edges: [] }
    } else if (selectedNodes.length > 0) {
      const selectedIds = new Set(selectedNodes.map(n => n.id))
      const relatedEdges = edges.filter(e => selectedIds.has(e.source) && selectedIds.has(e.target))
      clipboardRef.current = { nodes: selectedNodes, edges: relatedEdges }
    }
  }, [nodes, edges, selectedNode])

  const handlePasteNodes = useCallback(() => {
    if (!clipboardRef.current?.nodes?.length) return
    pushHistory()
    const idMap = {}
    const newNodes = clipboardRef.current.nodes.map(n => {
      const newId = getNodeId()
      idMap[n.id] = newId
      return {
        ...n,
        id: newId,
        position: { x: n.position.x + 50, y: n.position.y + 50 },
        selected: false,
      }
    })
    const newEdges = clipboardRef.current.edges.map(e => ({
      ...e,
      id: `edge_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      source: idMap[e.source] || e.source,
      target: idMap[e.target] || e.target,
    }))
    setNodes(nds => [...nds, ...newNodes])
    setEdges(eds => [...eds, ...newEdges])
    setHasChanges(true)
  }, [pushHistory, setNodes, setEdges])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); handleUndo() }
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && e.shiftKey) { e.preventDefault(); handleRedo() }
      if ((e.metaKey || e.ctrlKey) && e.key === 'y') { e.preventDefault(); handleRedo() }
      if ((e.metaKey || e.ctrlKey) && e.key === 'c') { handleCopyNodes() }
      if ((e.metaKey || e.ctrlKey) && e.key === 'v') { e.preventDefault(); handlePasteNodes() }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleUndo, handleRedo, handleCopyNodes, handlePasteNodes])

  useEffect(() => {
    if (!organizationId) return
    
    const fetchConfigs = async () => {
      try {
        const [llmRes, integrationsRes] = await Promise.all([
          llmConfigsApi.getAll(organizationId),
          integrationsApi.getAll(organizationId),
        ])
        
        setLlmConfigs(llmRes.data || [])
        
        const integrations = integrationsRes.data || []
        setEmailConfigs(integrations.filter(i => i.integration_type === 'email'))
        setSlackConfigs(integrations.filter(i => i.integration_type === 'slack'))
        setTeamsConfigs(integrations.filter(i => i.integration_type === 'teams'))
      } catch (err) {
        console.error('Failed to fetch configs:', err)
      }
    }
    
    fetchConfigs()
  }, [organizationId])

  useEffect(() => {
    if (workflow?.definition?.nodes) {
      const maxId = workflow.definition.nodes.reduce((max, node) => {
        const match = node.id.match(/node_(\d+)/)
        return match ? Math.max(max, parseInt(match[1], 10)) : max
      }, 0)
      nodeId = maxId + 1
    }
    
    if (workflow?.last_execution?.status === 'running' || workflow?.last_execution?.status === 'pending') {
      setCurrentExecutionId(workflow.last_execution.id)
      setExecutionStatus(workflow.last_execution.status)
      setIsExecuting(true)
    }
  }, [workflow])

  useEffect(() => {
    if (!currentExecutionId || !isExecuting) return

    const pollExecution = async () => {
      try {
        const response = await workflowsApi.getExecution(currentExecutionId)
        const execution = response.data
        setExecutionStatus(execution.status)
        
        const statuses = {}
        if (execution.logs) {
          execution.logs.forEach(log => {
            statuses[log.node_id] = log.status
          })
        }
        setNodeStatuses(statuses)
        
        if (execution.status !== 'running' && execution.status !== 'pending') {
          setIsExecuting(false)
          
          if (prevStatusRef.current !== execution.status) {
            if (execution.status === 'completed') {
              toast.success(`Workflow "${workflow?.name}" completed successfully`)
            } else if (execution.status === 'failed') {
              toast.error(`Workflow "${workflow?.name}" failed: ${execution.error_message || 'Unknown error'}`)
            }
          }
        }
        
        prevStatusRef.current = execution.status
      } catch (err) {
        console.error('Failed to poll execution:', err)
      }
    }

    pollExecution()
    const interval = setInterval(pollExecution, 2000)
    return () => clearInterval(interval)
  }, [currentExecutionId, isExecuting, toast, workflow?.name])

  const handleRunWorkflow = async () => {
    if (!workflow?.id || !workflow?.is_active) return
    
    try {
      const response = await workflowsApi.execute(workflow.id)
      setCurrentExecutionId(response.data.execution_id)
      setExecutionStatus('pending')
      setIsExecuting(true)
      setNodeStatuses({})
      prevStatusRef.current = null
      toast.info(`Workflow "${workflow?.name}" execution started`)
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || 'Failed to execute workflow')
    }
  }

  const getNodesWithStatus = useCallback(() => {
    return nodes.map(node => ({
      ...node,
      className: nodeStatuses[node.id] ? `node-status-${nodeStatuses[node.id]}` : '',
    }))
  }, [nodes, nodeStatuses])

  const getEdgesWithStatus = useCallback(() => {
    if (!isExecuting) return edges
    const completedNodes = new Set(
      Object.entries(nodeStatuses).filter(([, s]) => s === 'completed').map(([id]) => id)
    )
    const runningNodes = new Set(
      Object.entries(nodeStatuses).filter(([, s]) => s === 'running').map(([id]) => id)
    )
    return edges.map(edge => ({
      ...edge,
      animated: runningNodes.has(edge.source) || runningNodes.has(edge.target),
      style: completedNodes.has(edge.source) && completedNodes.has(edge.target)
        ? { stroke: '#10b981', strokeWidth: 2 }
        : edge.style,
    }))
  }, [edges, nodeStatuses, isExecuting])

  const onConnect = useCallback(
    (params) => {
      pushHistory()
      setEdges((eds) => addEdge({ ...params, animated: true }, eds))
      setHasChanges(true)
    },
    [setEdges, pushHistory]
  )

  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event) => {
      event.preventDefault()

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect()
      const nodeData = JSON.parse(event.dataTransfer.getData('application/reactflow'))

      if (!nodeData) return

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      })

      const newNode = {
        id: getNodeId(),
        type: nodeData.type,
        position,
        data: {
          label: nodeData.label,
          subType: nodeData.subType,
          config: {},
        },
      }

      setNodes((nds) => nds.concat(newNode))
      setHasChanges(true)
    },
    [reactFlowInstance, setNodes]
  )

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  const onNodeDataChange = useCallback(
    (nodeId, newData) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId ? { ...node, data: { ...node.data, ...newData } } : node
        )
      )
      setHasChanges(true)
    },
    [setNodes]
  )

  const onDeleteNode = useCallback(() => {
    if (!selectedNode) return
    setNodes((nds) => nds.filter((node) => node.id !== selectedNode.id))
    setEdges((eds) =>
      eds.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id)
    )
    setSelectedNode(null)
    setHasChanges(true)
  }, [selectedNode, setNodes, setEdges])

  const handleSave = () => {
    const definition = {
      nodes: nodes.map((node) => ({
        id: node.id,
        type: node.type,
        position: node.position,
        data: node.data,
      })),
      edges: edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle,
      })),
    }
    onSave(definition)
  }

  const onDragStart = (event, nodeData) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(nodeData))
    event.dataTransfer.effectAllowed = 'move'
  }

  const getCompletedNodeCount = () => {
    return Object.values(nodeStatuses).filter(s => s === 'completed').length
  }

  const getStatusLabel = () => {
    switch (executionStatus) {
      case 'pending': return 'Starting...'
      case 'running': return 'Running'
      case 'completed': return 'Completed'
      case 'failed': return 'Failed'
      default: return null
    }
  }

  return (
    <div className="workflow-editor">
      <div className="editor-header">
        <div className="editor-title">
          <h2>{workflow ? `Edit: ${workflow.name}` : 'New Workflow'}</h2>
          {hasChanges && <span className="unsaved-badge">Unsaved changes</span>}
        </div>
        <div className="editor-actions">
          {workflow?.id && (
            <button 
              className={`btn-run ${isExecuting ? 'running' : ''}`}
              onClick={handleRunWorkflow}
              disabled={isExecuting || !workflow.is_active}
            >
              {isExecuting ? (
                <>
                  <span className="run-spinner" />
                  Running...
                </>
              ) : (
                <>▶ Run</>
              )}
            </button>
          )}
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave}>
            Save Workflow
          </button>
        </div>
      </div>

      {executionStatus && (
        <div className={`execution-status-bar status-${executionStatus}`}>
          <div className="status-content">
            {isExecuting && <span className="status-spinner" />}
            <span className="status-label">{getStatusLabel()}</span>
            {isExecuting && nodes.length > 0 && (
              <span className="status-progress">
                {getCompletedNodeCount()}/{nodes.length} nodes completed
              </span>
            )}
          </div>
          {!isExecuting && (
            <button 
              className="status-dismiss" 
              onClick={() => setExecutionStatus(null)}
            >
              ×
            </button>
          )}
        </div>
      )}

      <div className="editor-body">
        <div className="node-palette">
          <h3>Nodes</h3>
          {nodeCategories.map((category) => (
            <div key={category.name} className="node-category">
              <h4>{category.name}</h4>
              <div className="node-list">
                {category.nodes.map((node) => (
                  <div
                    key={`${node.type}-${node.subType || ''}`}
                    className="palette-node"
                    draggable
                    onDragStart={(e) => onDragStart(e, node)}
                  >
                    <span className="node-icon">{node.icon}</span>
                    <span className="node-label">{node.label}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flow-canvas" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={getNodesWithStatus()}
            edges={getEdgesWithStatus()}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3, maxZoom: 1.5 }}
            defaultViewport={{ x: 0, y: 0, zoom: 1 }}
            minZoom={0.3}
            maxZoom={2}
            snapToGrid
            snapGrid={[10, 10]}
          >
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                switch (node.type) {
                  case 'trigger':
                  case 'chatbot_trigger':
                    return '#10b981'
                  case 'agent':
                    return '#6366f1'
                  case 'http':
                    return '#f59e0b'
                  case 'condition':
                  case 'switch':
                    return '#8b5cf6'
                  case 'loop':
                  case 'foreach':
                    return '#a855f7'
                  case 'fork':
                  case 'join':
                    return '#06b6d4'
                  case 'error_handler':
                    return '#ef4444'
                  case 'approval':
                    return '#f59e0b'
                  case 'delay':
                    return '#64748b'
                  case 'sub_workflow':
                    return '#3b82f6'
                  case 'email':
                    return '#ec4899'
                  case 'file_save':
                    return '#14b8a6'
                  case 'file_read':
                    return '#3b82f6'
                  case 'notification':
                    return '#f97316'
                  case 'webhook_response':
                    return '#22c55e'
                  case 'comment':
                    return '#fbbf24'
                  case 'group':
                    return '#94a3b8'
                  case 'database':
                    return '#8b5cf6'
                  case 'cloud_storage':
                    return '#06b6d4'
                  case 'google_sheets':
                    return '#22c55e'
                  case 'data_transform':
                    return '#f97316'
                  case 'python_code':
                    return '#3b82f6'
                  default:
                    return '#64748b'
                }
              }}
            />
            <Background variant="dots" gap={12} size={1} />
            <Panel position="top-right" className="flow-panel">
              <div className="panel-actions">
                <button className="panel-btn" onClick={handleUndo} title="Undo (Ctrl+Z)">↶</button>
                <button className="panel-btn" onClick={handleRedo} title="Redo (Ctrl+Shift+Z)">↷</button>
                <button className="panel-btn" onClick={handleCopyNodes} title="Copy (Ctrl+C)">⧉</button>
                <button className="panel-btn" onClick={handlePasteNodes} title="Paste (Ctrl+V)">📋</button>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {selectedNode && (
          <div className="node-config-panel">
            <div className="config-header">
              <h3>Node Configuration</h3>
              <button className="btn-delete" onClick={onDeleteNode}>
                Delete
              </button>
            </div>
            <NodeConfigForm
              node={selectedNode}
              onChange={(newData) => onNodeDataChange(selectedNode.id, newData)}
              llmConfigs={llmConfigs}
              emailConfigs={emailConfigs}
              slackConfigs={slackConfigs}
              teamsConfigs={teamsConfigs}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default WorkflowEditor
