// Generated from JSON-Schema - DO NOT EDIT BY HAND

class RunsJavascript {
  using "node12" | "node16" | "node20" @description("The application used to execute the code specified in `main`.")
  main string @description("The file that contains your action code. The application specified in `using` executes this file.")
  pre string? @description("Allows you to run a script at the start of a job, before the `main:` action begins. For example, you can use `pre:` to run a prerequisite setup script. The application specified with the `using` syntax will execute this file. The `pre:` action always runs by default but you can override this using `pre-if`.")
  pre_if PreIf?
  post string? @description("Allows you to run a script at the end of a job, once the `main:` action has completed. For example, you can use `post:` to terminate certain processes or remove unneeded files. The application specified with the `using` syntax will execute this file. The `post:` action always runs by default but you can override this using `post-if`.")
  post_if PostIf?
}

class PreIf {
  value string?
}

class PostIf {
  value string?
}

class RunsComposite {
  using string @description("To use a composite run steps action, set this to 'composite'.")
  steps Stepsitem[] @description("The run steps that you plan to run in this action.")
}

class Stepsitem {
  run string? @description("The command you want to run. This can be inline or a script in your action repository.")
  shell string? @description("The shell where you want to run the command.")
  uses string? @description("Selects an action to run as part of a step in your job.")
  with map<string, string>? @description("A map of the input parameters defined by the action. Each input parameter is a key/value pair. Input parameters are set as environment variables. The variable is prefixed with INPUT_ and converted to upper case.")
  name string? @description("The name of the composite run step.")
  id string? @description("A unique identifier for the step. You can use the `id` to reference the step in contexts.")
  if string? @description("You can use the if conditional to prevent a step from running unless a condition is met. You can use any supported context and expression to create a conditional. Expressions in an if conditional do not require the ${{ }} syntax. For more information, see https://help.github.com/en/articles/contexts-and-expression-syntax-for-github-actions.")
  environment map<string, string> | Stringcontainingexpressionsyntax? @description("Sets a map of environment variables for only that step.")
  continue_on_error bool | Expressionsyntax? @description("Prevents a job from failing when a step fails. Set to true to allow a job to pass when this step fails.")
  working_directory string? @description("Specifies the working directory where the command is run.")
}

class Stringcontainingexpressionsyntax {
  value string?
}

class Expressionsyntax {
  value string?
}

class RunsDocker {
  using string @description("You must set this value to 'docker'.")
  image string @description("The Docker image to use as the container to run the action. The value can be the Docker base image name, a local `Dockerfile` in your repository, or a public image in Docker Hub or another registry. To reference a `Dockerfile` local to your repository, use a path relative to your action metadata file. The `docker` application will execute this file.")
  environment map<string, string> | Stringcontainingexpressionsyntax? @description("Specifies a key/value map of environment variables to set in the container environment.")
  entrypoint string? @description("Overrides the Docker `ENTRYPOINT` in the `Dockerfile`, or sets it if one wasn't already specified. Use `entrypoint` when the `Dockerfile` does not specify an `ENTRYPOINT` or you want to override the `ENTRYPOINT` instruction. If you omit `entrypoint`, the commands you specify in the Docker `ENTRYPOINT` instruction will execute. The Docker `ENTRYPOINT instruction has a *shell* form and *exec* form. The Docker `ENTRYPOINT` documentation recommends using the *exec* form of the `ENTRYPOINT` instruction.")
  pre_entrypoint string? @description("Allows you to run a script before the `entrypoint` action begins. For example, you can use `pre-entrypoint:` to run a prerequisite setup script. GitHub Actions uses `docker run` to launch this action, and runs the script inside a new container that uses the same base image. This means that the runtime state is different from the main `entrypoint` container, and any states you require must be accessed in either the workspace, `HOME`, or as a `STATE_` variable. The `pre-entrypoint:` action always runs by default but you can override this using `pre-if`.")
  pre_if PreIf?
  post_entrypoint string? @description("Allows you to run a cleanup script once the `runs.entrypoint` action has completed. GitHub Actions uses `docker run` to launch this action. Because GitHub Actions runs the script inside a new container using the same base image, the runtime state is different from the main `entrypoint` container. You can access any state you need in either the workspace, `HOME`, or as a `STATE_` variable. The `post-entrypoint:` action always runs by default but you can override this using `post-if`.")
  post_if PostIf?
  args string[]? @description("An array of strings that define the inputs for a Docker container. Inputs can include hardcoded strings. GitHub passes the `args` to the container's `ENTRYPOINT` when the container starts up. The `args` are used in place of the `CMD` instruction in a `Dockerfile`. If you use `CMD` in your `Dockerfile`, use the guidelines ordered by preference: - Document required arguments in the action's README and omit them from the `CMD` instruction. - Use defaults that allow using the action without specifying any `args`. - If the action exposes a `--help` flag, or something similar, use that to make your action self-documenting.")
}

class Branding {
  color "white" | "black" | "yellow" | "blue" | "green" | "orange" | "red" | "purple" | "gray-dark"? @description("The background color of the badge.")
  icon Iconenum? @description("The name of the Feather icon to use.")
}

enum Iconenum {
  ACTIVITY
  AIRPLAY
  ALERT_CIRCLE
  ALERT_OCTAGON
  ALERT_TRIANGLE
  ALIGN_CENTER
  ALIGN_JUSTIFY
  ALIGN_LEFT
  ALIGN_RIGHT
  ANCHOR
  APERTURE
  ARCHIVE
  ARROW_DOWN_CIRCLE
  ARROW_DOWN_LEFT
  ARROW_DOWN_RIGHT
  ARROW_DOWN
  ARROW_LEFT_CIRCLE
  ARROW_LEFT
  ARROW_RIGHT_CIRCLE
  ARROW_RIGHT
  ARROW_UP_CIRCLE
  ARROW_UP_LEFT
  ARROW_UP_RIGHT
  ARROW_UP
  AT_SIGN
  AWARD
  BAR_CHART_2
  BAR_CHART
  BATTERY_CHARGING
  BATTERY
  BELL_OFF
  BELL
  BLUETOOTH
  BOLD
  BOOK_OPEN
  BOOK
  BOOKMARK
  BOX
  BRIEFCASE
  CALENDAR
  CAMERA_OFF
  CAMERA
  CAST
  CHECK_CIRCLE
  CHECK_SQUARE
  CHECK
  CHEVRON_DOWN
  CHEVRON_LEFT
  CHEVRON_RIGHT
  CHEVRON_UP
  CHEVRONS_DOWN
  CHEVRONS_LEFT
  CHEVRONS_RIGHT
  CHEVRONS_UP
  CIRCLE
  CLIPBOARD
  CLOCK
  CLOUD_DRIZZLE
  CLOUD_LIGHTNING
  CLOUD_OFF
  CLOUD_RAIN
  CLOUD_SNOW
  CLOUD
  CODE
  COMMAND
  COMPASS
  COPY
  CORNER_DOWN_LEFT
  CORNER_DOWN_RIGHT
  CORNER_LEFT_DOWN
  CORNER_LEFT_UP
  CORNER_RIGHT_DOWN
  CORNER_RIGHT_UP
  CORNER_UP_LEFT
  CORNER_UP_RIGHT
  CPU
  CREDIT_CARD
  CROP
  CROSSHAIR
  DATABASE
  DELETE
  DISC
  DOLLAR_SIGN
  DOWNLOAD_CLOUD
  DOWNLOAD
  DROPLET
  EDIT_2
  EDIT_3
  EDIT
  EXTERNAL_LINK
  EYE_OFF
  EYE
  FAST_FORWARD
  FEATHER
  FILE_MINUS
  FILE_PLUS
  FILE_TEXT
  FILE
  FILM
  FILTER
  FLAG
  FOLDER_MINUS
  FOLDER_PLUS
  FOLDER
  GIFT
  GIT_BRANCH
  GIT_COMMIT
  GIT_MERGE
  GIT_PULL_REQUEST
  GLOBE
  GRID
  HARD_DRIVE
  HASH
  HEADPHONES
  HEART
  HELP_CIRCLE
  HOME
  IMAGE
  INBOX
  INFO
  ITALIC
  LAYERS
  LAYOUT
  LIFE_BUOY
  LINK_2
  LINK
  LIST
  LOADER
  LOCK
  LOG_IN
  LOG_OUT
  MAIL
  MAP_PIN
  MAP
  MAXIMIZE_2
  MAXIMIZE
  MENU
  MESSAGE_CIRCLE
  MESSAGE_SQUARE
  MIC_OFF
  MIC
  MINIMIZE_2
  MINIMIZE
  MINUS_CIRCLE
  MINUS_SQUARE
  MINUS
  MONITOR
  MOON
  MORE_HORIZONTAL
  MORE_VERTICAL
  MOVE
  MUSIC
  NAVIGATION_2
  NAVIGATION
  OCTAGON
  PACKAGE
  PAPERCLIP
  PAUSE_CIRCLE
  PAUSE
  PERCENT
  PHONE_CALL
  PHONE_FORWARDED
  PHONE_INCOMING
  PHONE_MISSED
  PHONE_OFF
  PHONE_OUTGOING
  PHONE
  PIE_CHART
  PLAY_CIRCLE
  PLAY
  PLUS_CIRCLE
  PLUS_SQUARE
  PLUS
  POCKET
  POWER
  PRINTER
  RADIO
  REFRESH_CCW
  REFRESH_CW
  REPEAT
  REWIND
  ROTATE_CCW
  ROTATE_CW
  RSS
  SAVE
  SCISSORS
  SEARCH
  SEND
  SERVER
  SETTINGS
  SHARE_2
  SHARE
  SHIELD_OFF
  SHIELD
  SHOPPING_BAG
  SHOPPING_CART
  SHUFFLE
  SIDEBAR
  SKIP_BACK
  SKIP_FORWARD
  SLASH
  SLIDERS
  SMARTPHONE
  SPEAKER
  SQUARE
  STAR
  STOP_CIRCLE
  SUN
  SUNRISE
  SUNSET
  TABLE
  TABLET
  TAG
  TARGET
  TERMINAL
  THERMOMETER
  THUMBS_DOWN
  THUMBS_UP
  TOGGLE_LEFT
  TOGGLE_RIGHT
  TRASH_2
  TRASH
  TRENDING_DOWN
  TRENDING_UP
  TRIANGLE
  TRUCK
  TV
  TYPE
  UMBRELLA
  UNDERLINE
  UNLOCK
  UPLOAD_CLOUD
  UPLOAD
  USER_CHECK
  USER_MINUS
  USER_PLUS
  USER_X
  USER
  USERS
  VIDEO_OFF
  VIDEO
  VOICEMAIL
  VOLUME_1
  VOLUME_2
  VOLUME_X
  VOLUME
  WATCH
  WIFI_OFF
  WIFI
  WIND
  X_CIRCLE
  X_SQUARE
  X
  ZAP_OFF
  ZAP
  ZOOM_IN
  ZOOM_OUT
}

class Root {
  name string @description("The name of your action. GitHub displays the `name` in the Actions tab to help visually identify actions in each job.")
  author string? @description("The name of the action's author.")
  inputs map<string, string>? @description("Input parameters allow you to specify data that the action expects to use during runtime. GitHub stores input parameters as environment variables. Input ids with uppercase letters are converted to lowercase during runtime. We recommended using lowercase input ids.")
  outputs string?
  runs RunsJavascript | RunsComposite | RunsDocker
  branding Branding? @description("You can use a color and Feather icon to create a badge to personalize and distinguish your action. Badges are shown next to your action name in GitHub Marketplace.")
}

 
// This is our LLM function we can call in Python or Typescript
// the receipt can be an image OR text here!
function ExtractReceipt(receipt: string) -> Root {
  // see clients.baml
  client Gemini
  prompt #"
    {# start a user message #}
    {{ _.role("user") }}

    Extract info from this given data:
    {{ receipt }}

    Here is the format in which the output is expected:
    {# special macro to print the output schema instructions. #}
    {{ ctx.output_format }}
  "#
}

// Test when the input is an image
test ImageReceiptTest {
  functions [ExtractReceipt]
  args {
    receipt #"
      # "MkDocs Publisher" Action

I keep repeating the steps to build and deploy our MkDocs documentation sites to GitHub Pages across different repos. Let's create a reusable composite action to handle this.

Action Name: MkDocs Publisher
Purpose: A simple action to build an MkDocs site and push it to the gh-pages branch. Should be easy to use. Author should be listed as 'DevRel Team'.

Inputs Needed:

python-version: We need to specify the Python version for setting up the environment. Users should be able to choose. Let's make this optional and default it to 3.11. Description: 'The version of Python to set up for building.'
requirements-file: Users might have different requirements files (e.g., requirements.txt, docs/requirements.txt). This input should specify the path. It's required. Description: 'Path to the Python requirements file'.
gh-token: The GitHub token for pushing to gh-pages. This is absolutely required. Description: 'GitHub token for deployment.' Let's add a note that this is usually ${{ secrets.GITHUB_TOKEN }}. We should probably add a deprecation message to this input later if we find a better way, maybe: "Prefer using GITHUB_TOKEN environment variable directly if permissions allow."
Outputs:

The action needs to output the URL where the site was deployed. Let's call this output page-url. Its description should be 'The URL of the deployed GitHub Pages site.' The actual value should come from the deployment step (see below).

How it Runs (Execution):

This will be a composite action (using: composite). Here are the steps involved:

Checkout Code: First, we need the repository code. Use the standard actions/checkout@v4.
Setup Python: Next, set up the Python environment. Use actions/setup-python@v5. We must use the python-version input provided by the user here. Let's ID this step as setup_python.
Install Dependencies: Run a command to install the Python packages. The command is pip install -r ${{ inputs.requirements-file }}. Execute this using the bash shell. Maybe give this step the name "Install Python Packages".
Build Site: Run the command mkdocs build. Use bash for this too.
Deploy to Pages: Use an existing action for the deployment. peaceiris/actions-gh-pages@v3 seems popular. Give this step the ID deploy. We need to configure it:
Set its github_token parameter to the gh-token input we defined earlier.
Set its publish_dir parameter to ./site (which is the default build output dir for MkDocs).
Maybe add a condition (if:): github.ref == 'refs/heads/main' so it only deploys from the main branch.

Remember the page-url output? Its value needs to be linked to the output of the deploy step. So, for the page-url output, the value should be ${{ steps.deploy.outputs.page_url }}.

Branding:
For the marketplace look, let's use the color blue and the book-open icon. Looks professional.
    "#
  }
}
