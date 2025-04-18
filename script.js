document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropArea = document.getElementById("drop-area")
  const fileInput = document.getElementById("fileInput")
  const fileInfo = document.getElementById("file-info")
  const fileName = document.getElementById("file-name")
  const removeFileBtn = document.getElementById("remove-file")
  const uploadBtn = document.getElementById("upload-btn")
  const progressContainer = document.getElementById("progress-container")
  const progressBar = document.getElementById("progress")
  const progressText = document.getElementById("progress-text")
  const resultContainer = document.getElementById("result-container")
  const downloadBtn = document.getElementById("download-btn")
  const newUploadBtn = document.getElementById("new-upload-btn")
  const toast = document.getElementById("toast")
  const toastIcon = document.getElementById("toast-icon")
  const toastMessage = document.getElementById("toast-message")
  const themeToggle = document.getElementById("theme-toggle")
  const logo = document.getElementById("logo")
  const promptInput = document.getElementById("prompt-input")
  const promptInfoIcon = document.getElementById("prompt-info-icon")
  const promptTooltip = document.getElementById("prompt-tooltip")
  const usedPrompt = document.getElementById("used-prompt")

  // API endpoint (replace with your FastAPI backend URL if necessary)
  const API_URL = "http://localhost:8000/process"

  let selectedFile = null
  let currentTaskId = null
  let statusCheckInterval = null
  let darkMode = localStorage.getItem("darkMode") === "enabled"
  let currentPrompt = "Find all objects"
  let processedFileUrl = null

  // Initialize theme
  if (darkMode) {
    enableDarkMode()
  }

  // Theme toggle event listener
  themeToggle.addEventListener("click", toggleDarkMode)

  // Prompt info tooltip
  promptInfoIcon.addEventListener("mouseenter", () => {
    promptTooltip.classList.remove("hidden")
  })

  promptInfoIcon.addEventListener("mouseleave", () => {
    promptTooltip.classList.add("hidden")
  })

  // Prevent default drag behaviors
  ;["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropArea.addEventListener(eventName, preventDefaults, false)
    document.body.addEventListener(eventName, preventDefaults, false)
  })

  // Highlight drop area when item is dragged over it
  ;["dragenter", "dragover"].forEach((eventName) => {
    dropArea.addEventListener(eventName, highlight, false)
  })
  ;["dragleave", "drop"].forEach((eventName) => {
    dropArea.addEventListener(eventName, unhighlight, false)
  })

  // Handle dropped files
  dropArea.addEventListener("drop", handleDrop, false)

  // Handle file selection via input
  fileInput.addEventListener("change", handleFiles)

  // Handle click on drop area
  dropArea.addEventListener("click", () => {
    fileInput.click()
  })

  // Handle remove file button
  removeFileBtn.addEventListener("click", removeFile)

  // Handle upload button
  uploadBtn.addEventListener("click", uploadFile)

  // Handle download button
  downloadBtn.addEventListener("click", downloadFile)

  // Handle new upload button
  newUploadBtn.addEventListener("click", resetUI)

  function preventDefaults(e) {
    e.preventDefault()
    e.stopPropagation()
  }

  function highlight() {
    dropArea.classList.add("highlight")
  }

  function unhighlight() {
    dropArea.classList.remove("highlight")
  }

  function handleDrop(e) {
    const dt = e.dataTransfer
    const files = dt.files
    handleFiles(files)
  }

  function handleFiles(e) {
    let files
    if (e.target && e.target.files) {
      files = e.target.files
    } else {
      files = e
    }

    if (files.length) {
      const file = files[0]
      if (file.type === "application/zip" || file.name.endsWith(".zip")) {
        selectedFile = file
        displayFileInfo(file)
      } else {
        showToast("error", "Please select a ZIP file containing images")
      }
    }
  }

  function displayFileInfo(file) {
    fileName.textContent = file.name
    dropArea.classList.add("hidden")
    fileInfo.classList.remove("hidden")
  }

  function removeFile() {
    selectedFile = null
    fileInput.value = ""
    fileInfo.classList.add("hidden")
    dropArea.classList.remove("hidden")
  }

  function uploadFile() {
    if (!selectedFile) {
      showToast("error", "Please select a file first")
      return
    }

    // Get the prompt value
    currentPrompt = promptInput.value.trim()
    if (!currentPrompt) {
      currentPrompt = "Find all objects"
      promptInput.value = currentPrompt
    }

    // Update the used prompt text
    usedPrompt.textContent = currentPrompt

    // Show progress
    progressContainer.classList.remove("hidden")
    uploadBtn.disabled = true
    uploadBtn.textContent = "Processing..."

    const formData = new FormData()
    formData.append("file", selectedFile)
    formData.append("prompt", currentPrompt)

    fetch(API_URL, {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
    .then(data => {
      currentTaskId = data.task_id;
      
      // Start checking status periodically
      statusCheckInterval = setInterval(checkProcessingStatus, 2000);
      
      showToast('success', 'File uploaded successfully, processing started');
    })
    .catch(error => {
      console.error('Error:', error);
      showToast('error', 'An error occurred during upload');
      resetProgress();
    });
  }

  function checkProcessingStatus() {
    if (!currentTaskId) return

    fetch(`http://localhost:8000/status/${currentTaskId}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "processing") {
          // Update progress bar
          const progress = data.progress || 0
          progressBar.style.width = progress + "%"
          progressText.textContent = progress + "%"
        } else if (data.status === "completed") {
          // Processing complete
          clearInterval(statusCheckInterval)
          progressBar.style.width = "100%"
          progressText.textContent = "100%"
          showResultUI()
        } else if (data.status === "error") {
          // Error occurred
          clearInterval(statusCheckInterval)
          showToast("error", data.message || "An error occurred during processing")
          resetProgress()
        }
      })
      .catch((error) => {
        console.error("Error checking status:", error)
      })
  }

  function resetProgress() {
    progressBar.style.width = "0%"
    progressText.textContent = "0%"
    progressContainer.classList.add("hidden")
    uploadBtn.disabled = false
    uploadBtn.textContent = "Process File"
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval)
    }
  }

  function showResultUI() {
    fileInfo.classList.add("hidden")
    resultContainer.classList.remove("hidden")
    showToast("success", "File processed successfully!")
  }

  function downloadFile() {
    if (!currentTaskId) {
      showToast("error", "No processed file available")
      return
    }

    window.location.href = `http://localhost:8000/download/${currentTaskId}`
  }

  function resetUI() {
    resultContainer.classList.add("hidden")
    dropArea.classList.remove("hidden")
    resetProgress()
    selectedFile = null
    currentTaskId = null
    fileInput.value = ""
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval)
    }
  }

  function showToast(type, message) {
    toastIcon.className = "fas"
    if (type === "success") {
      toastIcon.classList.add("fa-check-circle")
    } else {
      toastIcon.classList.add("fa-exclamation-circle")
    }

    toastMessage.textContent = message
    toast.classList.remove("hidden")
    toast.classList.add("show")

    setTimeout(() => {
      toast.classList.remove("show")
      setTimeout(() => {
        toast.classList.add("hidden")
      }, 300)
    }, 3000)
  }

  // Dark mode functions
  function enableDarkMode() {
    document.body.classList.add("dark-mode")
    themeToggle.innerHTML = '<i class="fas fa-sun"></i>'
    logo.src = "logo-dark.png"
    darkMode = true
    localStorage.setItem("darkMode", "enabled")
  }

  function disableDarkMode() {
    document.body.classList.remove("dark-mode")
    themeToggle.innerHTML = '<i class="fas fa-moon"></i>'
    logo.src = "logo.png"
    darkMode = false
    localStorage.setItem("darkMode", "disabled")
  }

  function toggleDarkMode() {
    if (darkMode) {
      disableDarkMode()
    } else {
      enableDarkMode()
    }

    // Show a toast notification
    showToast("success", darkMode ? "Dark mode enabled" : "Light mode enabled")
  }
})