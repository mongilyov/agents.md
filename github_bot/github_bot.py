#!/usr/bin/env python3
"""Repository-scoped GitHub App authentication. Python stdlib + OpenSSL + Git."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class BotError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward authentication to a redirect destination.


def http_error_diagnostic(method, path, error, authenticated):
    # Only bounded numeric rate-limit headers are safe to echo. Never read the
    # response body, Authorization, arbitrary headers, or server reason text.
    fields = {}
    for header, label in [('X-RateLimit-Limit', 'limit'),
                          ('X-RateLimit-Remaining', 'remaining'),
                          ('X-RateLimit-Reset', 'reset_epoch'),
                          ('Retry-After', 'retry_after_seconds')]:
        value = (error.headers or {}).get(header, '')
        if re.fullmatch(r'[0-9]{1,20}', value):
            fields[label] = value
    auth = 'authenticated' if authenticated else 'unauthenticated'
    message = f'GitHub {method} {path}: HTTP {error.code} ({auth} request).'
    if fields:
        message += ' Rate-limit headers: ' + ', '.join(f'{k}={v}' for k, v in fields.items()) + '.'
    if error.code in (403, 429):
        if fields.get('remaining') == '0':
            message += ' GitHub primary rate limit exhausted; wait until reset before retrying.'
        elif error.code == 429 or 'retry_after_seconds' in fields:
            message += ' GitHub indicates throttling/rate limiting; honor Retry-After before retrying.'
        else:
            message += ' The cause is not established: rate limiting or an access policy may apply to this request.'
    elif error.code == 401:
        message += ' Authentication was rejected for this request.'
    elif error.code >= 500:
        message += ' GitHub server error; a write may have succeeded. Do not blindly retry.'
    else:
        message += ' Inspect this endpoint and its request requirements.'
    return message


def api(method, path, token, data=None):
    if not path.startswith('/') or path.startswith('//'):
        raise BotError('Invalid API path')
    request = urllib.request.Request(
        'https://api.github.com' + path,
        data=None if data is None else json.dumps(data).encode(),
        method=method,
        headers={**({'Authorization': 'Bearer ' + token} if token else {}),
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json',
                 'X-GitHub-Api-Version': '2026-03-10',
                 'User-Agent': 'local-github-bot-helper'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raise BotError(http_error_diagnostic(method, path, error, bool(token))) from None
    except urllib.error.URLError:
        raise BotError('Cannot connect to GitHub (network or TLS error).') from None


def encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


def jwt(config):
    now = int(time.time())
    header = encode(b'{"alg":"RS256","typ":"JWT"}')
    payload = encode(json.dumps({'iat': now - 60, 'exp': now + 540,
                                 'iss': str(config['app_id'])}).encode())
    unsigned = (header + '.' + payload).encode()
    result = subprocess.run(['openssl', 'dgst', '-sha256', '-sign',
                             str(Path(config['private_key']).expanduser())],
                            input=unsigned, capture_output=True)
    if result.returncode:
        raise BotError('OpenSSL could not sign with the configured private key.')
    return unsigned.decode() + '.' + encode(result.stdout)


def normalize_repo(value):
    value = value.removeprefix('https://github.com/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise BotError('Repository must be OWNER/REPO or an HTTPS github.com URL.')
    return value


class Session:
    def __init__(self, config):
        self.repo = normalize_repo(config['repository'])
        self.config = config
        self.token = None
        self.permissions = {}

    def __enter__(self):
        app_jwt = jwt(self.config)
        app = api('GET', '/app', app_jwt)
        if int(app['id']) != int(self.config['app_id']):
            raise BotError('Unexpected app identity')
        installation = api('GET', f"/app/installations/{self.config['installation_id']}", app_jwt)
        if installation['account']['login'].lower() != self.repo.split('/')[0].lower():
            raise BotError('Repository owner does not match the installation account.')
        if installation.get('suspended_at'):
            raise BotError('This installation is suspended.')
        grant = api('POST', f"/app/installations/{self.config['installation_id']}/access_tokens",
                    app_jwt, {'repositories': [self.repo.split('/')[1]]})
        self.token = grant['token']
        try:
            self.permissions = grant.get('permissions', {})
            self.expires = grant['expires_at']
            bot = api('GET', '/users/' + urllib.parse.quote(app['slug'] + '[bot]'), self.token)
            self.login = bot['login']
            self.email = f"{bot['id']}+{self.login}@users.noreply.github.com"
        except BaseException:
            self.__exit__()  # Context-manager exit is not invoked when enter fails.
            raise
        return self

    def __exit__(self, *args):
        if self.token is None:
            return
        try:
            api('DELETE', '/installation/token', self.token)
        except (BotError, OSError, ValueError, KeyError):
            print('Note: token revocation failed; the token will expire automatically.', file=sys.stderr)
        finally:
            self.token = None

    def request(self, method, suffix, data=None):
        return api(method, '/repos/' + self.repo + suffix, self.token, data)

    def pages(self, suffix):
        items = []
        for page in range(1, 10001):
            batch = self.request('GET', f'{suffix}?per_page=100&page={page}')
            items.extend(batch)
            if len(batch) < 100:
                return items
        raise BotError('Too many comments to paginate.')

    def require(self, permission):
        if self.permissions.get(permission) != 'write':
            raise BotError(f'The app needs {permission}: write for this operation.')


def credential():
    fields = dict(line.rstrip('\n').split('=', 1) for line in sys.stdin if '=' in line)
    if (sys.argv[-1] == 'get' and fields.get('protocol') == 'https'
            and fields.get('host') == 'github.com'
            and fields.get('path', '').removesuffix('.git') == os.environ.get('BOT_REPOSITORY')):
        print('username=x-access-token')
        print('password=' + os.environ['BOT_INSTALLATION_TOKEN'])
    # Never persist credentials on store/erase.


def git_run(session, checkout, arguments, identity=False):
    if arguments[0] in ('commit', 'push', 'fetch'):
        origin = subprocess.run(['git', '-C', str(checkout), 'remote', 'get-url', 'origin'],
                                capture_output=True, text=True, check=True).stdout.strip()
        origin = origin.removeprefix('git@github.com:').removeprefix('ssh://git@github.com/')
        if normalize_repo(origin).lower() != session.repo.lower():
            raise BotError('Checkout origin does not match the selected repository.')
    env = os.environ.copy()
    # Disable diagnostics that could expose HTTP credentials.
    for name in list(env):
        if name.startswith('GIT_TRACE') or name in ('GIT_CURL_VERBOSE', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
            env.pop(name, None)
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['GIT_ASKPASS'] = '/usr/bin/false'
    env['BOT_INSTALLATION_TOKEN'] = session.token
    env['BOT_REPOSITORY'] = session.repo
    if identity:
        env.update(GIT_AUTHOR_NAME=session.login, GIT_COMMITTER_NAME=session.login,
                   GIT_AUTHOR_EMAIL=session.email, GIT_COMMITTER_EMAIL=session.email)
    helper = '!' + shlex.join([sys.executable, str(Path(__file__).resolve()), '_credential'])
    command = ['git', '-C', str(checkout), '-c', 'credential.helper=',
               '-c', 'credential.helper=' + helper, '-c', 'credential.useHttpPath=true',
               '-c', 'http.extraHeader=', '-c', 'http.followRedirects=false'] + arguments
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    for value, stream in ((result.stdout, sys.stdout), (result.stderr, sys.stderr)):
        stream.write(value.replace(session.token, '[REDACTED]'))
    if result.returncode:
        raise BotError(f'Git exited with status {result.returncode}.')


def body_file(path):
    body = Path(path).read_text()
    if not body.strip():
        raise BotError('Body file is empty.')
    return body


def get_open_pr(session, number, same_head_repo=False):
    if number <= 0:
        raise BotError('PR numbers must be positive.')
    pr = session.request('GET', f'/pulls/{number}')
    sides = ('base', 'head') if same_head_repo else ('base',)
    if pr.get('number') != number or any(
        ((pr.get(side) or {}).get('repo') or {}).get('full_name', '').lower() != session.repo.lower()
        for side in sides
    ):
        raise BotError(f'PR #{number} does not belong to the selected repository; cross-fork stacks are unsupported.')
    if pr.get('state') != 'open' or pr.get('merged') or pr.get('merged_at'):
        raise BotError(f'PR #{number} must be open and unmerged.')
    return pr


def mark_ready(session, number):
    session.require('pull_requests')
    pr = get_open_pr(session, number)
    if pr.get('draft') is False:
        return pr
    if pr.get('draft') is not True:
        raise BotError('GitHub did not return a valid draft state.')
    query = '''mutation($id: ID!) {
      markPullRequestReadyForReview(input: {pullRequestId: $id}) {
        pullRequest { id isDraft }
      }
    }'''
    try:
        result = api('POST', '/graphql', session.token,
                     {'query': query, 'variables': {'id': pr['node_id']}})
        if result.get('errors') or not result.get('data'):
            # GraphQL error text is untrusted and may contain sensitive values.
            raise BotError('GitHub could not mark the PR ready for review.')
    except BotError:
        # A concurrent operation or a lost response may already have completed it.
        current = get_open_pr(session, number)
        if current.get('draft') is False:
            return current
        raise
    current = get_open_pr(session, number)
    if current.get('draft') is not False:
        raise BotError('PR is still a draft after the ready operation; inspect GitHub before retrying.')
    return current


def existing_stack(session, numbers):
    memberships = [session.request('GET', f'/stacks?pull_request={n}') for n in numbers]
    if not any(memberships):
        return None
    if not all(len(stacks) == 1 for stacks in memberships):
        raise BotError('Some PRs already belong to a stack; refusing to change existing membership.')
    stack_number = memberships[0][0]['number']
    if any(stacks[0]['number'] != stack_number for stacks in memberships):
        raise BotError('PRs already belong to different stacks.')
    stack = session.request('GET', f'/stacks/{stack_number}')
    if not stack.get('open') or [pr['number'] for pr in stack['pull_requests']] != numbers:
        raise BotError('Existing stack differs from the exact requested order or membership.')
    return stack


def register_stack(session, numbers):
    session.require('pull_requests')
    if len(numbers) < 2 or len(set(numbers)) != len(numbers) or any(n <= 0 for n in numbers):
        raise BotError('Supply at least two distinct positive PR numbers, bottom to top.')
    prs = [get_open_pr(session, n, same_head_repo=True) for n in numbers]
    heads = [pr['head']['ref'] for pr in prs]
    if len(set(heads)) != len(heads) or prs[0]['base']['ref'] in heads:
        raise BotError('Stack branches must be distinct and must not form a cycle.')
    for lower, upper in zip(prs, prs[1:]):
        if upper['base']['ref'] != lower['head']['ref']:
            raise BotError(f"PR #{upper['number']} must target the head branch of PR #{lower['number']}.")
    stack = existing_stack(session, numbers)
    if stack:
        return stack
    try:
        session.request('POST', '/stacks', {'pull_requests': numbers})
    except BotError:
        # Never blindly repeat a write after an ambiguous response.
        stack = existing_stack(session, numbers)
        if stack:
            return stack
        raise
    stack = existing_stack(session, numbers)
    if not stack:
        raise BotError('Stack creation was not confirmed. Inspect GitHub before retrying.')
    return stack


def create_pr(session, args):
    session.require('pull_requests')
    return session.request('POST', '/pulls', {
        'title': args.title, 'head': args.head,
        'base': args.base or session.request('GET', '')['default_branch'],
        'body': body_file(args.body_file), 'draft': not args.ready})



def permission_report(permissions):
    required = {'metadata': 'read', 'contents': 'write', 'pull_requests': 'write',
                'checks': 'read', 'actions': 'read', 'statuses': 'read'}
    ranks = {'read': 1, 'write': 2, 'admin': 3}
    missing = [f'{name}:{level}' for name, level in required.items()
               if ranks.get(permissions.get(name), 0) < ranks[level]]
    return {'required': required, 'missing': missing,
            'note': 'Grants do not bypass branch protections. Workflow-file changes may also need workflows:write.'}


def request_review(session, number, reviewers, rerequest=False):
    session.require('pull_requests')
    pr = get_open_pr(session, number)
    if pr.get('draft') is not False:
        raise BotError('Mark the PR ready before requesting review.')
    if not reviewers or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', r) for r in reviewers):
        raise BotError('Supply valid reviewer usernames.')
    reviewers = list(dict.fromkeys(r.lower() for r in reviewers))
    if (pr.get('user') or {}).get('login', '').lower() in reviewers:
        raise BotError('A PR author cannot review their own PR.')
    pending = {r['login'].lower(): r for r in pr.get('requested_reviewers', [])}
    requested = reviewers if rerequest else [r for r in reviewers if r not in pending]
    if requested:
        # Never retry or switch transports after an ambiguous notification write.
        if rerequest:
            users = []
            for login in requested:
                user = pending.get(login, {})
                if not user.get('node_id') or user.get('type') != 'User':
                    user = api('GET', '/users/' + urllib.parse.quote(login, safe=''), session.token)
                if (user.get('login', '').lower() != login or user.get('type') != 'User'
                        or not user.get('node_id')):
                    raise BotError('GitHub did not confirm the reviewer identity.')
                users.append(user['node_id'])
            query = '''mutation($id: ID!, $users: [ID!]!) {
              rerequestReviews(input: {pullRequestId: $id, userIds: $users}) {
                pullRequest { id }
              }
            }'''
            result = api('POST', '/graphql', session.token,
                         {'query': query, 'variables': {'id': pr['node_id'], 'users': users}})
            payload = ((result.get('data') or {}).get('rerequestReviews') or {}).get('pullRequest') or {}
            if result.get('errors') or payload.get('id') != pr['node_id']:
                # Pending reviewers alone cannot prove a fresh notification succeeded.
                # Do not echo untrusted GraphQL messages or retry the mutation.
                raise BotError('GitHub did not confirm the review re-request; inspect the PR before retrying.')
        else:
            session.request('POST', f'/pulls/{number}/requested_reviewers', {'reviewers': requested})
    current = get_open_pr(session, number) if requested else pr
    pending = {r['login'].lower() for r in current.get('requested_reviewers', [])}
    if not set(reviewers).issubset(pending):
        raise BotError('Review request was not confirmed; inspect the PR before retrying.')
    return {'url': current['html_url'], 'reviewers': reviewers,
            'action': ('rerequested' if rerequest else 'requested') if requested else 'already requested',
            'notification_delivery': 'GitHub controls delivery; not independently verified.'}


def read_checks(session, number):
    pr = get_open_pr(session, number)
    sha = pr['head']['sha']
    ref = urllib.parse.quote(sha, safe='')
    result = {'head_sha': sha}
    sources = [('check_runs', f'/commits/{ref}/check-runs', 'check_runs'),
               ('statuses', f'/commits/{ref}/status', 'statuses'),
               ('workflow_runs', f'/actions/runs?head_sha={ref}', 'workflow_runs')]
    for name, path, key in sources:
        items = []
        try:
            for page in range(1, 10001):
                sep = '&' if '?' in path else '?'
                data = session.request('GET', f'{path}{sep}per_page=100&page={page}')
                items.extend(data[key])
                if len(data[key]) < 100:
                    break
            else:
                raise BotError('Too many check results to paginate.')
            result[name] = {'items': items}
            if name == 'statuses':
                result[name]['state'] = data['state']
        except BotError as error:
            result[name] = {'error': str(error)}
    if get_open_pr(session, number)['head']['sha'] != sha:
        raise BotError('PR head changed during check lookup; rerun checks for the new head.')
    return result


def edit_pr(session, number, title=None, body=None):
    session.require('pull_requests')
    get_open_pr(session, number)
    data = {k: v for k, v in [('title', title), ('body', body)] if v is not None}
    if not data or any(not v.strip() for v in data.values()):
        raise BotError('Supply a nonempty title or body.')
    session.request('PATCH', f'/pulls/{number}', data)
    current = get_open_pr(session, number)
    if any(current.get(k) != v for k, v in data.items()):
        raise BotError('PR update was not confirmed; inspect before retrying.')
    return current


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-id', type=int, help='GitHub App ID from project settings')
    p.add_argument('--installation-id', type=int, help='Installation ID from project settings')
    p.add_argument('--repo', help='Explicit repository from project settings: OWNER/REPO')
    p.add_argument('--checkout', help='Absolute path to the actual working checkout')
    commands = p.add_subparsers(dest='command', required=True)
    commands.add_parser('check', help='Verify bot, token scope, permissions, and HTTPS Git read access')
    commands.add_parser('fetch', help='Fetch origin with isolated bot credentials; never merge')
    c = commands.add_parser('pr', help='Read an open PR and requested reviewers')
    c.add_argument('--pr', required=True, type=int)
    c = commands.add_parser('edit-pr', help='Update only supplied PR title/body and verify')
    c.add_argument('--pr', required=True, type=int)
    c.add_argument('--title')
    c.add_argument('--body-file')
    c = commands.add_parser('checks', help='Read checks, statuses, and Actions runs for an open PR head')
    c.add_argument('--pr', required=True, type=int)
    c = commands.add_parser('request-review', help='Request reviewers; explicitly re-notify with --rerequest')
    c.add_argument('--pr', required=True, type=int)
    c.add_argument('--reviewers', required=True, nargs='+')
    c.add_argument('--rerequest', action='store_true', help='Send a fresh review notification once')
    c = commands.add_parser('commit', help='Commit already-staged changes as the bot')
    c.add_argument('--message-file', required=True)
    c = commands.add_parser('push', help='Push one named local branch to the selected repository')
    c.add_argument('--branch', required=True)
    c = commands.add_parser('comments', help='Read conversation comments, inline comments, and reviews')
    c.add_argument('--pr', required=True, type=int)
    c = commands.add_parser('reply', help='Post a PR conversation comment or inline-thread reply')
    c.add_argument('--pr', required=True, type=int)
    c.add_argument('--body-file', required=True)
    c.add_argument('--review-comment-id', type=int, help='Inline comment ID, not a conversation comment ID')
    c = commands.add_parser('ready', help='Mark an existing draft PR ready for review')
    c.add_argument('--pr', required=True, type=int)
    c = commands.add_parser('stack', help='Register existing PRs as a native GitHub stack, bottom to top')
    c.add_argument('--prs', required=True, nargs='+', type=int)
    c = commands.add_parser('create-pr', help='Create a PR (draft by default); --base supports stacked PRs')
    c.add_argument('--ready', action='store_true', help='Create ready for review instead of draft')
    c.add_argument('--head', required=True)
    c.add_argument('--base', help='Defaults to the repository default branch; specify parent branch for a stack')
    c.add_argument('--title', required=True)
    c.add_argument('--body-file', required=True)
    return p


def runtime_settings(args):
    # Nonsecret values come explicitly from AGENTS.md via CLI arguments.
    for name in ('app_id', 'installation_id'):
        value = getattr(args, name)
        if value is None or value <= 0:
            raise BotError('Supply a positive --' + name.replace('_', '-') + ' from AGENTS.md.')
    if not args.repo or not args.checkout:
        raise BotError('Supply --repo from AGENTS.md and --checkout for the actual working checkout.')
    checkout = Path(args.checkout).expanduser()
    if not checkout.is_absolute():
        raise BotError('--checkout must be an absolute path.')
    key_path = os.environ.get('GITHUB_APP_PRIVATE_KEY_PATH')
    if not key_path:
        raise BotError('Set GITHUB_APP_PRIVATE_KEY_PATH to the private-key file path; ask the user for the path, never the key contents.')
    key = Path(key_path).expanduser()
    if not key.is_absolute() or not key.is_file():
        raise BotError('GITHUB_APP_PRIVATE_KEY_PATH must identify an existing absolute file path.')
    return {'app_id': args.app_id, 'installation_id': args.installation_id,
            'repository': normalize_repo(args.repo), 'checkout': str(checkout),
            'private_key': str(key)}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_credential':
        credential()
        return
    args = parser().parse_args()
    config = runtime_settings(args)
    checkout = Path(config['checkout']).expanduser()
    with Session(config) as session:
        url = 'https://github.com/' + session.repo + '.git'
        if args.command == 'check':
            scoped = api('GET', '/installation/repositories', session.token)
            repos = [repo['full_name'] for repo in scoped['repositories']]
            if scoped['total_count'] != 1 or [r.lower() for r in repos] != [session.repo.lower()]:
                raise BotError('Token scope was not exactly the selected repository.')
            repo = session.request('GET', '')
            print(json.dumps({'bot': session.login, 'commit_email': session.email,
                              'app_id': config['app_id'], 'installation_id': config['installation_id'],
                              'token_repositories': repos, 'permissions': session.permissions,
                              'default_branch': repo['default_branch'], 'expires_at': session.expires,
                              'workflow_permissions': permission_report(session.permissions)}, indent=2))
            git_run(session, checkout, ['ls-remote', url, 'HEAD'])
            print('Verified HTTPS Git read access. No repository content or comments were changed.')
        elif args.command == 'fetch':
            git_run(session, checkout, ['fetch', 'origin'])
        elif args.command == 'pr':
            print(json.dumps(get_open_pr(session, args.pr), indent=2))
        elif args.command == 'edit-pr':
            result = edit_pr(session, args.pr, args.title, body_file(args.body_file) if args.body_file else None)
            print(result['html_url'])
        elif args.command == 'checks':
            print(json.dumps(read_checks(session, args.pr), indent=2))
        elif args.command == 'request-review':
            print(json.dumps(request_review(session, args.pr, args.reviewers, args.rerequest), indent=2))
        elif args.command == 'commit':
            git_run(session, checkout, ['commit', '--file', str(Path(args.message_file).resolve())], identity=True)
        elif args.command == 'push':
            session.require('contents')
            subprocess.run(['git', 'check-ref-format', 'refs/heads/' + args.branch], check=True, capture_output=True)
            git_run(session, checkout, ['push', url, f'refs/heads/{args.branch}:refs/heads/{args.branch}'])
        elif args.command == 'comments':
            session.request('GET', f'/pulls/{args.pr}')
            print(json.dumps({'conversation': session.pages(f'/issues/{args.pr}/comments'),
                              'inline': session.pages(f'/pulls/{args.pr}/comments'),
                              'reviews': session.pages(f'/pulls/{args.pr}/reviews')}, indent=2))
        elif args.command == 'reply':
            session.request('GET', f'/pulls/{args.pr}')  # Refuse an issue number that is not a PR.
            suffix = f'/issues/{args.pr}/comments'
            if args.review_comment_id:
                session.require('pull_requests')
                comment = session.request('GET', f'/pulls/comments/{args.review_comment_id}')
                if comment['pull_request_url'] != f'https://api.github.com/repos/{session.repo}/pulls/{args.pr}':
                    raise BotError('Review comment belongs to a different PR.')
                root = comment.get('in_reply_to_id', comment['id'])
                suffix = f'/pulls/{args.pr}/comments/{root}/replies'
            result = session.request('POST', suffix, {'body': body_file(args.body_file)})
            print(result['html_url'])
        elif args.command == 'create-pr':
            print(create_pr(session, args)['html_url'])
        elif args.command == 'ready':
            result = mark_ready(session, args.pr)
            print(f"Ready for review: {result['html_url']}")
        elif args.command == 'stack':
            result = register_stack(session, args.prs)
            print(json.dumps({'stack_number': result['number'],
                              'pull_requests': [pr['number'] for pr in result['pull_requests']]}, indent=2))



if __name__ == '__main__':
    try:
        main()
    except (BotError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        if isinstance(error, BotError):
            print('Error: ' + str(error), file=sys.stderr)
        else:
            print('Error: local configuration or command failed (' + type(error).__name__ + ').', file=sys.stderr)
        sys.exit(1)
