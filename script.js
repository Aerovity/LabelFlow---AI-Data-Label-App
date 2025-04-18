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

  // API endpoint (replace with your FastAPI backend URL)
  const API_URL = "http://localhost:8000/process"

  let selectedFile = null
  let processedFileUrl = null
  let darkMode = localStorage.getItem("darkMode") === "enabled"

  // Initialize theme
  if (darkMode) {
    enableDarkMode()
  }

  // Theme toggle event listener
  themeToggle.addEventListener("click", toggleDarkMode)

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
        showToast("error", "Please select a ZIP file")
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

    // Show progress
    progressContainer.classList.remove("hidden")
    uploadBtn.disabled = true
    uploadBtn.textContent = "Processing..."

    const formData = new FormData()
    formData.append("file", selectedFile)

    // Simulate progress (in a real app, you'd use XHR or fetch with progress events)
    simulateProgress()

    // In a real application, you would use this:
    /*
        fetch(API_URL, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.blob();
        })
        .then(blob => {
            processedFileUrl = URL.createObjectURL(blob);
            showResultUI();
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('error', 'An error occurred during processing');
            resetProgress();
        });
        */

    // For demo purposes, we'll simulate a successful response after 3 seconds
    setTimeout(() => {
      // Create a dummy blob for demo purposes
      const dummyBlob = new Blob(["dummy content"], { type: "application/zip" })
      processedFileUrl = URL.createObjectURL(dummyBlob)
      showResultUI()
    }, 3000)
  }

  function simulateProgress() {
    let width = 0
    const interval = setInterval(() => {
      if (width >= 100) {
        clearInterval(interval)
      } else {
        width += 5
        progressBar.style.width = width + "%"
        progressText.textContent = width + "%"
      }
    }, 150)
  }

  function resetProgress() {
    progressBar.style.width = "0%"
    progressText.textContent = "0%"
    progressContainer.classList.add("hidden")
    uploadBtn.disabled = false
    uploadBtn.textContent = "Process File"
  }

  function showResultUI() {
    fileInfo.classList.add("hidden")
    resultContainer.classList.remove("hidden")
    showToast("success", "File processed successfully!")
  }

  function downloadFile() {
    if (processedFileUrl) {
      const a = document.createElement("a")
      a.href = processedFileUrl
      a.download = "processed_" + selectedFile.name
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
  }

  function resetUI() {
    resultContainer.classList.add("hidden")
    dropArea.classList.remove("hidden")
    resetProgress()
    selectedFile = null
    fileInput.value = ""
    if (processedFileUrl) {
      URL.revokeObjectURL(processedFileUrl)
      processedFileUrl = null
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
